# Развёртывание на сервере

Стек описан в `backend/docker-compose.prod.yml`. Наружу открыт только Caddy
(80/443), он сам получает сертификаты Let's Encrypt и раздаёт:

| Адрес | Что там |
|---|---|
| `https://cifrovye-zodchie.ru` | сайт; `/api/*` и `/health` — бэкенд |
| `https://files.cifrovye-zodchie.ru` | файловое хранилище (S3, presigned URL) |
| `https://judge0.cifrovye-zodchie.ru` | Judge0, только с заголовком `X-Auth-Token` |

Postgres, SeaweedFS, воркер и служебные сервисы Judge0 доступны только во
внутренней сети docker.

## 1. Сервер

- **ОС: Ubuntu 22.04 / 24.04 LTS или Debian 12.** Judge0 1.13 нужен cgroup v1,
  а systemd 256+ (Ubuntu 24.10+, Debian 13) его уже не поддерживает.
- Ресурсы: от 4 ГБ RAM и 40 ГБ диска (образ Judge0 весит ~14 ГБ).

## 2. DNS

A-записи на IP сервера для трёх имён: `cifrovye-zodchie.ru`,
`files.cifrovye-zodchie.ru`, `judge0.cifrovye-zodchie.ru`. Без них Caddy не
получит сертификаты.

## 3. cgroup v1 для Judge0

```bash
sudo sed -i 's/^GRUB_CMDLINE_LINUX="/&systemd.unified_cgroup_hierarchy=0 /' /etc/default/grub
sudo update-grub && sudo reboot
# после перезагрузки должно быть tmpfs (cgroup v1), а не cgroup2fs:
stat -fc %T /sys/fs/cgroup
```

## 4. Docker и файрвол

Docker Engine: https://docs.docker.com/engine/install/ubuntu/

```bash
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 443/udp
sudo ufw enable
```

## 5. Настройки

```bash
git clone <repo> zebra && cd zebra/backend
cp .env.example .env
```

В `.env` заменить все `change-me` на случайные значения
(`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`) и указать
`ACME_EMAIL`. Строки `CORS_ORIGINS`, `S3_PUBLIC_ENDPOINT`, `JUDGE0_URL` на
сервере ни на что не влияют: prod-compose задаёт их сам по доменам.

## 6. Запуск

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl https://cifrovye-zodchie.ru/health
```

Проверка Judge0 (должен вернуть `"stdout":"4\n"`, статус `Accepted`):

```bash
curl -s -X POST "https://judge0.cifrovye-zodchie.ru/submissions?wait=true" \
  -H "X-Auth-Token: <JUDGE0_AUTH_TOKEN из .env>" -H "Content-Type: application/json" \
  -d '{"language_id": 71, "source_code": "print(2 * 2)"}'
```

Первый администратор (пользователь должен сначала зарегистрироваться на сайте):

```bash
docker compose -f docker-compose.prod.yml exec backend \
  uv run --no-sync python src/set_role.py <username> admin
```

## 7. Разработчикам

Локальный воркер тоже проверяет код на серверном Judge0: в локальном `.env`
укажите `JUDGE0_AUTH_TOKEN` из серверного `.env` (`JUDGE0_URL` уже указывает
на сервер). Токен даёт право запускать код на сервере — не публикуйте его.

## Обновление и бэкапы

```bash
git pull && docker compose -f docker-compose.prod.yml up -d --build
```

Данные лежат в томах `zebra_pgdata` (база), `zebra_s3data` (файлы) и
`zebra_caddy_data` (сертификаты). Дамп базы:

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup-$(date +%F).sql
```
