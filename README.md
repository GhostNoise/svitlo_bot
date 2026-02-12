# Ping Monitor Telegram Bot

Моніторинг доступності IPv4 адреси через ICMP ping з повідомленнями в Telegram.

## Налаштування

### 1. Отримати Telegram Bot Token

1. Напишіть [@BotFather](https://t.me/BotFather) в Telegram
2. Відправте `/newbot`
3. Дайте ім'я та username боту
4. Скопіюйте токен

### 2. Отримати Chat ID

**Варіант А:** Напишіть [@userinfobot](https://t.me/userinfobot) — він покаже ваш ID.

**Варіант Б:**
1. Напишіть будь-що вашому боту
2. Відкрийте: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Знайдіть `"chat":{"id":123456789}`

### 3. Створити .env файл

```bash
cp .env.example .env
```

Заповніть значення:
```
TELEGRAM_BOT_TOKEN=ваш_токен
TELEGRAM_CHAT_ID=ваш_chat_id
TARGET_IPV4=IP_для_моніторингу
CHECK_INTERVAL_SECONDS=180
TZ=Europe/Kiev
```

## Запуск

```bash
docker compose up -d
```

## Логи

```bash
docker compose logs -f
```

## Зупинка

```bash
docker compose down
```

## Формат повідомлень

При зникненні зв'язку:
```
14:35 Світло зникло
Воно було 2год 15хв
```

При відновленні:
```
16:50 Світло з'явилося
Його не було 2год 15хв
```
