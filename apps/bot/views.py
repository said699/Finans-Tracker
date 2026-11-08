import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from aiogram.types import Update
from .handlers import dp
from django.conf import settings
from aiogram import Bot

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

@csrf_exempt
async def telegram_webhook(request):
    if request.method == 'POST':
        try:
            json_data = json.loads(request.body.decode('utf-8'))
            update = Update.model_validate(json_data, context={"bot": bot})
            await dp.feed_update(bot, update)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)