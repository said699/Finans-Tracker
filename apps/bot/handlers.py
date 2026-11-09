import re
from decimal import Decimal, InvalidOperation
from functools import wraps

from aiogram import Dispatcher, F, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup,
)
from asgiref.sync import sync_to_async
from django.contrib.auth import authenticate
from django.db import close_old_connections
from django.utils import timezone

from apps.finans.forms import (
    AddCategoryForm, AddEarningCategoryForm, AddEarningForm, AddPaymentForm,
)
from apps.finans.models import (
    CURRENCY_CHOICES, Earnings, EarningCategory, Payment, PayCategory,
)
from apps.users.forms import RegisterForm
from apps.users.models import CustomUser

dp = Dispatcher()
dp.message.filter(F.chat.type == "private")  # пароли не должны попадать в группы
dp.callback_query.filter(F.message.chat.type == "private")

CURRENCIES = [code for code, _ in CURRENCY_CHOICES]
NOT_AUTH = (False, "Сначала войди или зарегистрируйся (кнопки внизу, /menu).")
MAX_LOGIN_ATTEMPTS = 5
NO_NOTE = "Без описания"  # на сайте описание обязательно

#Кнопки меню

BTN_PAY, BTN_EARN = "➖ Расход", "➕ Доход"
BTN_PAYS, BTN_EARNS = "📋 Расходы", "📋 Доходы"
BTN_PCATS, BTN_ECATS = "🗂 Категории расходов", "🗂 Категории доходов"
BTN_LOGIN, BTN_REG, BTN_LOGOUT = "🔑 Войти", "📝 Регистрация", "🚪 Выйти"

MENU_ACTIONS = {
    BTN_PAY: ("add", "pay"), BTN_EARN: ("add", "earn"),
    BTN_PAYS: ("list", "pay"), BTN_EARNS: ("list", "earn"),
    BTN_PCATS: ("cats", "pay"), BTN_ECATS: ("cats", "earn"),
}

# Всё различие между расходами и доходами собрано здесь
KINDS = {
    "pay": dict(
        cat_model=PayCategory, tx_model=Payment,
        cat_form=AddCategoryForm, tx_form=AddPaymentForm,
        cat_word="расходов", tx_word="Расход", tx_plural="расходы", sign="-",
        cat_btn=BTN_PCATS,
    ),
    "earn": dict(
        cat_model=EarningCategory, tx_model=Earnings,
        cat_form=AddEarningCategoryForm, tx_form=AddEarningForm,
        cat_word="доходов", tx_word="Доход", tx_plural="доходы", sign="+",
        cat_btn=BTN_ECATS,
    ),
}

COLORS = [
    ("🔴", "E53935"), ("🟠", "FB8C00"), ("🟡", "FDD835"), ("🟢", "43A047"),
    ("🔵", "1E88E5"), ("🟣", "8E24AA"), ("🟤", "6D4C41"), ("⚫", "424242"),
]

HELP = (
    "Привет! Я финансовый бот. Всё управляется кнопками внизу.\n\n"
    "<b>Быстрый ввод</b> (если так удобнее):\n"
    "<code>-100 USD Еда Обед</code> — расход\n"
    "<code>+500 USD Зарплата Аванс</code> — доход\n"
    "<code>-30 USD \"Кафе и рестораны\" Ужин</code> — категория из нескольких слов\n\n"
    "/menu — показать кнопки\n"
    "/cancel — отменить текущее действие\n\n"
    f"Валюты: {', '.join(CURRENCIES)}"
)


def main_menu(logged_in: bool) -> ReplyKeyboardMarkup:
    if logged_in:
        rows = [
            [BTN_PAY, BTN_EARN],
            [BTN_PAYS, BTN_EARNS],
            [BTN_PCATS, BTN_ECATS],
            [BTN_LOGOUT],
        ]
    else:
        rows = [[BTN_LOGIN, BTN_REG]]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in rows],
        resize_keyboard=True,
    )


def btn(text, data):
    return InlineKeyboardButton(text=text, callback_data=data)


def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chunk(items, n):
    return [items[i:i + n] for i in range(0, len(items), n)]


def short(s, n=55):
    return s if len(s) <= n else s[:n - 1] + "…"


CANCEL_BTN = btn("❌ Отмена", "cancel")
CANCEL_KB = kb([[CANCEL_BTN]])
NOTE_KB = kb([[btn("⏭ Пропустить", "note_skip")], [CANCEL_BTN]])
COLOR_KB = kb(
    chunk([btn(emoji, f"catcol:{hx}") for emoji, hx in COLORS], 4) + [[CANCEL_BTN]]
)


#Вспомогательное

def db(func):
    """sync -> async + закрытие старых соединений Django."""
    @sync_to_async
    @wraps(func)
    def wrapper(*args, **kwargs):
        close_old_connections()
        try:
            return func(*args, **kwargs)
        finally:
            close_old_connections()
    return wrapper


async def reply(message: types.Message, result):
    ok, text = result
    await message.answer(("✅ " if ok else "❌ ") + text)


async def show(target, text, markup=None):
    """Для кнопки редактирует сообщение, для обычного сообщения отправляет новое."""
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass  # например, "message is not modified"
        await target.answer()
    else:
        await target.answer(text, reply_markup=markup)


async def safe_delete(message: types.Message):
    try:
        await message.delete()
    except Exception:
        pass


def form_errors(form) -> str:
    parts = []
    for field, errs in form.errors.items():
        label = form.fields[field].label if field in form.fields else None
        text = " ".join(errs)
        parts.append(f"{label}: {text}" if label else text)
    return "; ".join(parts)


def parse_amount(raw):
    """Возвращает (Decimal, None) или (None, текст ошибки)."""
    try:
        amount = Decimal(raw.strip().replace(",", ".").replace(" ", ""))
    except InvalidOperation:
        return None, "Некорректная сумма."
    if not amount.is_finite():
        return None, "Некорректная сумма."
    if amount >= Decimal("100000000"):
        return None, "Слишком большая сумма."
    amount = amount.quantize(Decimal("0.01"))
    if amount <= 0:
        return None, "Сумма должна быть больше нуля."
    return amount, None


def get_user(tg_id):
    return CustomUser.objects.filter(telegram_id=tg_id).first()


def find_category(model, user, name):
    cats = list(model.objects.filter(user=user, name=name)[:2])
    if not cats:
        cats = list(model.objects.filter(user=user, name__iexact=name)[:2])
    if not cats:
        return None, "Категория не найдена."
    if len(cats) > 1:
        return None, "Найдено несколько категорий с таким названием. Объедини их на сайте."
    return cats[0], None


def tx_label(k, t):
    cat = t.category.name if t.category else "без категории"
    return f"{k['sign']}{t.amount} {t.currency} · {cat} · {timezone.localtime(t.date_done):%d.%m.%Y}"


#Состояния диалогов

class Reg(StatesGroup):
    username = State()
    email = State()
    phone = State()
    password = State()


class Login(StatesGroup):
    username = State()
    password = State()


class AddTx(StatesGroup):
    category = State()
    currency = State()
    amount = State()
    note = State()


class AddCat(StatesGroup):
    name = State()
    color = State()


#Работа с БД

@db
def linked_username(tg_id):
    user = get_user(tg_id)
    return user.username if user else None


@db
def check_register_field(field, data):
    form = RegisterForm(data)
    form.is_valid()
    errs = form.errors.get(field)
    return " ".join(errs) if errs else None


@db
def register_user(tg_id, data, password):
    if CustomUser.objects.filter(telegram_id=tg_id).exists():
        return "fail", "Этот Telegram уже привязан к аккаунту. Сначала выйди."
    form = RegisterForm({**data, "password1": password, "password2": password})
    if not form.is_valid():
        bad = set(form.errors)
        status = "retry" if bad <= {"password1", "password2"} else "fail"
        return status, form_errors(form)
    user = form.save()
    user.telegram_id = tg_id
    user.save(update_fields=["telegram_id"])
    return "ok", f"Аккаунт {user.username} создан, ты вошёл. Начни с создания категорий: кнопки внизу."


@db
def login_user(tg_id, username, password):
    user = authenticate(username=username, password=password)
    if user is None:
        return False, "Неверный логин или пароль."
    CustomUser.objects.filter(telegram_id=tg_id).exclude(pk=user.pk).update(telegram_id=None)
    user.telegram_id = tg_id
    user.save(update_fields=["telegram_id"])
    return True, f"Ты вошёл как {user.username}."


@db
def logout_user(tg_id):
    updated = CustomUser.objects.filter(telegram_id=tg_id).update(telegram_id=None)
    return (True, "Ты вышел из аккаунта.") if updated else (False, "Ты и так не авторизован.")


@db
def list_categories(kind, tg_id):
    user = get_user(tg_id)
    if not user:
        return NOT_AUTH
    cats = KINDS[kind]["cat_model"].objects.filter(user=user).order_by("name")
    return True, [(c.pk, c.name, c.color) for c in cats]


@db
def category_name_error(kind, tg_id, name):
    user = get_user(tg_id)
    if not user:
        return NOT_AUTH[1]
    if len(name) > 100:
        return "Название слишком длинное (максимум 100 символов)."
    if KINDS[kind]["cat_model"].objects.filter(user=user, name=name).exists():
        return "У тебя уже есть категория с таким названием."
    return None


@db
def create_category(kind, tg_id, name, color):
    user = get_user(tg_id)
    if not user:
        return NOT_AUTH
    k = KINDS[kind]
    form = k["cat_form"]({"name": name, "color": color}, user=user)
    if not form.is_valid():
        return False, form_errors(form)
    cat = form.save(commit=False)
    cat.user = user
    cat.save()
    return True, f"Категория {k['cat_word']} «{cat.name}» создана."


@db
def category_info(kind, tg_id, pk):
    user = get_user(tg_id)
    if not user:
        return NOT_AUTH
    k = KINDS[kind]
    cat = k["cat_model"].objects.filter(user=user, pk=pk).first()
    if not cat:
        return False, "Категория не найдена (возможно, уже удалена)."
    return True, (cat.name, k["tx_model"].objects.filter(user=user, category=cat).count())


@db
def delete_category(kind, tg_id, pk):
    user = get_user(tg_id)
    if not user:
        return NOT_AUTH
    k = KINDS[kind]
    cat = k["cat_model"].objects.filter(user=user, pk=pk).first()
    if not cat:
        return False, "Категория не найдена."
    title = cat.name
    cat.delete()
    return True, f"Категория {k['cat_word']} «{title}» удалена."


@db
def save_transaction(kind, tg_id, amount, currency, note, category_name=None, category_id=None):
    user = get_user(tg_id)
    if not user:
        return NOT_AUTH
    k = KINDS[kind]
    if category_id is not None:
        category = k["cat_model"].objects.filter(user=user, pk=category_id).first()
        err = None if category else "Категория не найдена."
    else:
        category, err = find_category(k["cat_model"], user, category_name)
    if err:
        return False, f"{err} Создай её в разделе «{k['cat_btn']}»."

    form = k["tx_form"](
        {"amount": str(amount), "currency": currency, "category": str(category.pk), "note": note},
        user=user,
    )
    if not form.is_valid():
        return False, form_errors(form)
    obj = form.save(commit=False)
    obj.user = user
    obj.save()
    return True, f"{k['tx_word']} записан: {k['sign']}{obj.amount} {obj.currency} ({category.name})"


@db
def list_transactions(kind, tg_id):
    user = get_user(tg_id)
    if not user:
        return NOT_AUTH
    k = KINDS[kind]
    items = (
        k["tx_model"].objects.filter(user=user)
        .select_related("category").order_by("-date_done", "-pk")[:10]
    )
    return True, [(t.pk, tx_label(k, t)) for t in items]


@db
def tx_info(kind, tg_id, pk):
    user = get_user(tg_id)
    if not user:
        return NOT_AUTH
    k = KINDS[kind]
    t = k["tx_model"].objects.filter(pk=pk, user=user).select_related("category").first()
    if not t:
        return False, f"{k['tx_word']} не найден (возможно, уже удалён)."
    note = f"\n{t.note}" if t.note else ""
    return True, tx_label(k, t) + note


@db
def delete_transaction(kind, tg_id, pk):
    user = get_user(tg_id)
    if not user:
        return NOT_AUTH
    deleted, _ = KINDS[kind]["tx_model"].objects.filter(pk=pk, user=user).delete()
    return (True, "Запись удалена.") if deleted else (False, "Запись не найдена.")


#Меню, помощь, отмена

async def menu(message: types.Message, text, parse_mode=None):
    logged_in = bool(await linked_username(message.from_user.id))
    await message.answer(text, reply_markup=main_menu(logged_in), parse_mode=parse_mode)


@dp.message(CommandStart())
@dp.message(Command("help"))
@dp.message(Command("menu"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await menu(message, HELP, parse_mode="HTML")


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await menu(message, "Отменено.")


@dp.callback_query(F.data == "cancel")
async def cb_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, "Отменено.")


#Кнопки главного меню
@dp.message(F.text.in_(MENU_ACTIONS))
async def menu_action(message: types.Message, state: FSMContext):
    await state.clear()
    action, kind = MENU_ACTIONS[message.text]
    tg_id = message.from_user.id
    if action == "add":
        await start_add_tx(message, state, kind)
    elif action == "list":
        await show_tx_list(message, kind, tg_id)
    else:
        await show_cat_list(message, kind, tg_id)


@dp.message(Command("register"))
@dp.message(F.text == BTN_REG)
async def cmd_register(message: types.Message, state: FSMContext):
    await state.clear()
    name = await linked_username(message.from_user.id)
    if name:
        await menu(message, f"Ты уже вошёл как {name}. Чтобы сменить аккаунт, нажми «{BTN_LOGOUT}».")
        return
    await state.set_state(Reg.username)
    await message.answer("Регистрация. Придумай логин:", reply_markup=CANCEL_KB)


@dp.message(Command("login"))
@dp.message(F.text == BTN_LOGIN)
async def cmd_login(message: types.Message, state: FSMContext):
    await state.clear()
    name = await linked_username(message.from_user.id)
    if name:
        await menu(message, f"Ты уже вошёл как {name}. Чтобы сменить аккаунт, нажми «{BTN_LOGOUT}».")
        return
    await state.set_state(Login.username)
    await state.update_data(attempts=0)
    await message.answer("Введи логин:", reply_markup=CANCEL_KB)


@dp.message(Command("logout"))
@dp.message(F.text == BTN_LOGOUT)
async def cmd_logout(message: types.Message, state: FSMContext):
    await state.clear()
    ok, text = await logout_user(message.from_user.id)
    await menu(message, ("✅ " if ok else "❌ ") + text)


#Регистрация

@dp.message(Reg.username, F.text)
async def reg_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    err = await check_register_field("username", {"username": username})
    if err:
        await message.answer(f"❌ {err}\nПопробуй другой логин:", reply_markup=CANCEL_KB)
        return
    await state.update_data(username=username)
    await state.set_state(Reg.email)
    await message.answer("Введи email:", reply_markup=CANCEL_KB)


@dp.message(Reg.email, F.text)
async def reg_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    err = await check_register_field("email", {"email": email})
    if err:
        await message.answer(f"❌ {err}\nВведи другой email:", reply_markup=CANCEL_KB)
        return
    await state.update_data(email=email)
    await state.set_state(Reg.phone)
    await message.answer("Введи номер телефона:", reply_markup=CANCEL_KB)


@dp.message(Reg.phone, F.text)
async def reg_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    err = await check_register_field("phone", {"phone": phone})
    if err:
        await message.answer(f"❌ {err}\nВведи номер телефона:", reply_markup=CANCEL_KB)
        return
    await state.update_data(phone=phone)
    await state.set_state(Reg.password)
    await message.answer(
        "Придумай пароль. Сообщение с ним я сразу удалю.\n"
        "Этот же пароль будет работать на сайте.",
        reply_markup=CANCEL_KB,
    )


@dp.message(Reg.password, F.text)
async def reg_password(message: types.Message, state: FSMContext):
    password = message.text
    await safe_delete(message)
    data = await state.get_data()
    status, text = await register_user(message.from_user.id, data, password)
    if status == "retry":
        await message.answer(f"❌ {text}\nВведи другой пароль:", reply_markup=CANCEL_KB)
        return
    await state.clear()
    await menu(message, ("✅ " if status == "ok" else "❌ ") + text)



@dp.message(Login.username, F.text)
async def login_username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text.strip())
    await state.set_state(Login.password)
    await message.answer("Введи пароль (сообщение будет удалено):", reply_markup=CANCEL_KB)


@dp.message(Login.password, F.text)
async def login_password(message: types.Message, state: FSMContext):
    password = message.text
    await safe_delete(message)
    data = await state.get_data()
    ok, text = await login_user(message.from_user.id, data["username"], password)
    if ok:
        await state.clear()
        await menu(message, "✅ " + text)
        return

    attempts = data.get("attempts", 0) + 1
    if attempts >= MAX_LOGIN_ATTEMPTS:
        await state.clear()
        await menu(message, "❌ Слишком много неудачных попыток. Начни заново.")
        return
    await state.update_data(attempts=attempts)
    await message.answer(f"❌ {text}\nПопробуй пароль ещё раз:", reply_markup=CANCEL_KB)


async def start_add_tx(target, state: FSMContext, kind):
    ok, cats = await list_categories(kind, target.from_user.id)
    if not ok:
        await show(target, "❌ " + cats)
        return
    k = KINDS[kind]
    if not cats:
        await show(
            target,
            f"У тебя пока нет категорий {k['cat_word']}. Сначала создай хотя бы одну.",
            kb([[btn("➕ Создать категорию", f"catnew:{kind}")]]),
        )
        return
    await state.set_state(AddTx.category)
    await state.update_data(kind=kind)
    buttons = [btn(name, f"txcat:{pk}") for pk, name, _ in cats]
    await show(target, f"{k['tx_word']}. Выбери категорию:", kb(chunk(buttons, 2) + [[CANCEL_BTN]]))


@dp.callback_query(AddTx.category, F.data.regexp(r"^txcat:\d+$"))
async def tx_category(cb: CallbackQuery, state: FSMContext):
    await state.update_data(category_id=int(cb.data.split(":")[1]))
    await state.set_state(AddTx.currency)
    buttons = [btn(label, f"txcur:{code}") for code, label in CURRENCY_CHOICES]
    await show(cb, "Выбери валюту:", kb(chunk(buttons, 2) + [[CANCEL_BTN]]))


@dp.callback_query(AddTx.currency, F.data.regexp(r"^txcur:[A-Z]{3}$"))
async def tx_currency(cb: CallbackQuery, state: FSMContext):
    code = cb.data.split(":")[1]
    if code not in CURRENCIES:
        await cb.answer("Неизвестная валюта")
        return
    await state.update_data(currency=code)
    await state.set_state(AddTx.amount)
    await show(cb, f"Введи сумму в {code}:", CANCEL_KB)


@dp.message(AddTx.amount, F.text)
async def tx_amount(message: types.Message, state: FSMContext):
    amount, err = parse_amount(message.text)
    if err:
        await message.answer(f"❌ {err}\nВведи сумму ещё раз:", reply_markup=CANCEL_KB)
        return
    await state.update_data(amount=str(amount))
    await state.set_state(AddTx.note)
    await message.answer("Напиши описание или пропусти этот шаг:", reply_markup=NOTE_KB)


async def finish_tx(target, state: FSMContext, note):
    data = await state.get_data()
    await state.clear()
    ok, text = await save_transaction(
        data["kind"], target.from_user.id, Decimal(data["amount"]),
        data["currency"], note, category_id=data["category_id"],
    )
    await show(target, ("✅ " if ok else "❌ ") + text)


@dp.message(AddTx.note, F.text)
async def tx_note(message: types.Message, state: FSMContext):
    note = message.text.strip()
    if len(note) > 300:
        await message.answer("❌ Максимум 300 символов. Сократи описание:", reply_markup=NOTE_KB)
        return
    await finish_tx(message, state, note or NO_NOTE)


@dp.callback_query(AddTx.note, F.data == "note_skip")
async def tx_note_skip(cb: CallbackQuery, state: FSMContext):
    await finish_tx(cb, state, NO_NOTE)


# ---------- Списки записей и удаление ----------

async def show_tx_list(target, kind, tg_id, prefix=""):
    ok, items = await list_transactions(kind, tg_id)
    if not ok:
        await show(target, "❌ " + items)
        return
    k = KINDS[kind]
    if not items:
        await show(target, prefix + f"Записей ({k['tx_plural']}) пока нет.")
        return
    rows = [[btn("🗑 " + short(label), f"txdel:{kind}:{pk}")] for pk, label in items]
    await show(
        target,
        prefix + f"Последние {k['tx_plural']}. Нажми на запись, чтобы удалить:",
        kb(rows),
    )


@dp.callback_query(F.data.regexp(r"^txlist:(pay|earn)$"))
async def cb_tx_list(cb: CallbackQuery):
    await show_tx_list(cb, cb.data.split(":")[1], cb.from_user.id)


@dp.callback_query(F.data.regexp(r"^txdel:(pay|earn):\d+$"))
async def cb_tx_del(cb: CallbackQuery):
    _, kind, pk = cb.data.split(":")
    ok, text = await tx_info(kind, cb.from_user.id, int(pk))
    if not ok:
        await show(cb, "❌ " + text)
        return
    await show(
        cb,
        f"Удалить запись?\n\n{text}",
        kb([
            [btn("✅ Да, удалить", f"txdelok:{kind}:{pk}")],
            [btn("↩️ Назад", f"txlist:{kind}")],
        ]),
    )


@dp.callback_query(F.data.regexp(r"^txdelok:(pay|earn):\d+$"))
async def cb_tx_del_ok(cb: CallbackQuery):
    _, kind, pk = cb.data.split(":")
    ok, text = await delete_transaction(kind, cb.from_user.id, int(pk))
    await show_tx_list(cb, kind, cb.from_user.id, prefix=("✅ " if ok else "❌ ") + text + "\n\n")


# ---------- Категории ----------

async def show_cat_list(target, kind, tg_id, prefix=""):
    ok, cats = await list_categories(kind, tg_id)
    if not ok:
        await show(target, "❌ " + cats)
        return
    k = KINDS[kind]
    if cats:
        text = (
            f"Категории {k['cat_word']}:\n"
            + "\n".join(f"• {name} ({color})" for _, name, color in cats)
            + "\n\nЧтобы удалить категорию, нажми на неё."
        )
    else:
        text = f"Категорий {k['cat_word']} пока нет."
    rows = chunk([btn("🗑 " + short(name, 30), f"catdel:{kind}:{pk}") for pk, name, _ in cats], 2)
    rows.append([btn("➕ Новая категория", f"catnew:{kind}")])
    await show(target, prefix + text, kb(rows))


@dp.callback_query(F.data.regexp(r"^catlist:(pay|earn)$"))
async def cb_cat_list(cb: CallbackQuery):
    await show_cat_list(cb, cb.data.split(":")[1], cb.from_user.id)


@dp.callback_query(F.data.regexp(r"^catdel:(pay|earn):\d+$"))
async def cb_cat_del(cb: CallbackQuery):
    _, kind, pk = cb.data.split(":")
    ok, info = await category_info(kind, cb.from_user.id, int(pk))
    if not ok:
        await show(cb, "❌ " + info)
        return
    name, orphaned = info
    warn = f"\nЗаписей без категории станет: {orphaned}." if orphaned else ""
    await show(
        cb,
        f"Удалить категорию «{name}»?{warn}",
        kb([
            [btn("✅ Да, удалить", f"catdelok:{kind}:{pk}")],
            [btn("↩️ Назад", f"catlist:{kind}")],
        ]),
    )


@dp.callback_query(F.data.regexp(r"^catdelok:(pay|earn):\d+$"))
async def cb_cat_del_ok(cb: CallbackQuery):
    _, kind, pk = cb.data.split(":")
    ok, text = await delete_category(kind, cb.from_user.id, int(pk))
    await show_cat_list(cb, kind, cb.from_user.id, prefix=("✅ " if ok else "❌ ") + text + "\n\n")


@dp.callback_query(F.data.regexp(r"^catnew:(pay|earn)$"))
async def cb_cat_new(cb: CallbackQuery, state: FSMContext):
    kind = cb.data.split(":")[1]
    await state.clear()
    await state.set_state(AddCat.name)
    await state.update_data(kind=kind)
    await show(cb, f"Введи название категории {KINDS[kind]['cat_word']}:", CANCEL_KB)


@dp.message(AddCat.name, F.text)
async def cat_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    data = await state.get_data()
    if not name:
        err = "Название не может быть пустым."
    else:
        err = await category_name_error(data["kind"], message.from_user.id, name)
    if err:
        await message.answer(f"❌ {err}\nВведи другое название:", reply_markup=CANCEL_KB)
        return
    await state.update_data(name=name)
    await state.set_state(AddCat.color)
    await message.answer("Выбери цвет кнопкой или введи свой HEX, например #FF8800:", reply_markup=COLOR_KB)


async def finish_cat(target, state: FSMContext, color):
    data = await state.get_data()
    ok, text = await create_category(data["kind"], target.from_user.id, data["name"], color)
    if not ok:
        await show(target, f"❌ {text}\nВыбери другой цвет или введи HEX:", COLOR_KB)
        return
    await state.clear()
    await show_cat_list(target, data["kind"], target.from_user.id, prefix="✅ " + text + "\n\n")


@dp.callback_query(AddCat.color, F.data.regexp(r"^catcol:[0-9a-fA-F]{6}$"))
async def cat_color_button(cb: CallbackQuery, state: FSMContext):
    await finish_cat(cb, state, "#" + cb.data.split(":")[1])


@dp.message(AddCat.color, F.text)
async def cat_color_text(message: types.Message, state: FSMContext):
    color = message.text.strip()
    if re.fullmatch(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}", color):
        color = "#" + color
    await finish_cat(message, state, color)



TX_START = r"^[+-]\s?\d"
TX_RE = re.compile(
    r'^([+-])\s?(\d+(?:[.,]\d+)?)\s+([A-Za-z]{3})\s+'
    r'(?:["«“](.+?)["»”]|(\S+))(?:\s+(.+))?$',
    re.S,
)


@dp.message(StateFilter(None), F.text.regexp(TX_START))
async def handle_transaction(message: types.Message):
    m = TX_RE.match(message.text.strip())
    if not m:
        await message.answer(
            "❌ Неверный формат.\n"
            "Расход: -100 USD Еда Обед\n"
            "Доход: +500 USD Зарплата Премия\n"
            'Категория из нескольких слов: -30 USD "Кафе и рестораны" Ужин\n\n'
            "Или пользуйся кнопками внизу."
        )
        return

    sign, raw_amount, currency, quoted, single, note = m.groups()
    currency = currency.upper()
    if currency not in CURRENCIES:
        await message.answer(f"❌ Валюта не поддерживается. Доступны: {', '.join(CURRENCIES)}")
        return
    amount, err = parse_amount(raw_amount)
    if err:
        await message.answer("❌ " + err)
        return

    await reply(message, await save_transaction(
        "earn" if sign == "+" else "pay",
        message.from_user.id, amount, currency,
        (note or "").strip() or NO_NOTE,
        category_name=(quoted or single).strip(),
    ))


@dp.callback_query()
async def cb_stale(cb: CallbackQuery):
    await cb.answer("Эта кнопка устарела. Открой меню заново: /menu", show_alert=True)