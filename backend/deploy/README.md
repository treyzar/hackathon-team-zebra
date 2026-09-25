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

Чтобы не писать `sudo` перед каждой командой docker:
`sudo usermod -aG docker $USER` и перелогиниться. Членство в группе `docker`
равносильно правам root — давайте его только администраторам сервера.

## 5. Настройки

```bash
git clone <repo> zebra && cd zebra/backend
cp .env.example .env
```

В `.env` заменить все `change-me` на случайные значения
(`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`) и указать
настоящий `ACME_EMAIL`. Проверка: `grep -n change-me .env` ничего не выводит.
Строки `CORS_ORIGINS`, `S3_PUBLIC_ENDPOINT`, `JUDGE0_URL` на сервере ни на что
не влияют: prod-compose задаёт их сам по доменам. Все переменные описаны в
корневом README, раздел «Переменные окружения».

## 6. Запуск

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl https://cifrovye-zodchie.ru/health
```

### Проверка Judge0

```bash
TOKEN=$(grep '^JUDGE0_AUTH_TOKEN=' .env | cut -d= -f2-)
J=https://judge0.cifrovye-zodchie.ru
run() { curl -s -X POST "$J/submissions?wait=true" -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" -d "$1"; echo; }

curl -s -o /dev/null -w "%{http_code}\n" $J/languages/71   # 401: без токена нельзя
run '{"language_id":71,"source_code":"print(int(input())**2)","stdin":"3","expected_output":"9"}'
# 3 Accepted, stdout "9\n"; "Internal Error ... /box/script.py" — нет cgroup v1 (шаг 3)
run '{"language_id":71,"source_code":"while True: pass","cpu_time_limit":1}'
# 5 Time Limit Exceeded
run '{"language_id":71,"source_code":"a = bytearray(600*1024*1024)","memory_limit":262144}'
# Runtime Error (MemoryError/SIGKILL), не Accepted
run '{"language_id":71,"source_code":"import urllib.request as u; u.urlopen(\"http://example.com\", timeout=3)"}'
# Runtime Error: у кода нет сети
run '{"language_id":71,"source_code":"print(1)","enable_network":true}'
# 422: enabling network is not allowed
```

Без DNS те же запросы можно отправить внутри сети docker:
`docker run --rm --network zebra_default curlimages/curl ... http://judge0-server:2358/...`.

### Первый администратор

Пользователь сначала регистрируется на сайте, затем:

```bash
docker compose -f docker-compose.prod.yml exec backend \
  uv run --no-sync python src/set_role.py <username> admin
```

## 7. Разработчикам

Локальный воркер тоже проверяет код на серверном Judge0: в локальном `.env`
укажите `JUDGE0_AUTH_TOKEN` из серверного `.env` (`JUDGE0_URL` уже указывает
на сервер). Токен даёт право запускать код на сервере — не публикуйте его.

## Обновление

```bash
git pull && docker compose -f docker-compose.prod.yml up -d --build
```

`--build` обязателен: код входит в образ, без пересборки запустится старая
версия. Миграции базы применяет сервис `migrate` при каждом запуске.

## Частые проблемы

| Симптом | Причина и решение |
|---|---|
| `curl: (35) ... tlsv1 alert internal error` | Caddy не получил сертификат: нет A-записи, закрыты порты 80/443 (в облаке — ещё и группа безопасности) или `ACME_EMAIL` на `example.com`. Причина — в `docker compose -f docker-compose.prod.yml logs caddy`; после исправления — `restart caddy` |
| `password authentication failed` у `migrate` | Пароль Postgres задаётся только при создании тома: том создан со старым `POSTGRES_PASSWORD`. Если данных нет — `down -v` и `up -d`, иначе `ALTER USER` |
| `password authentication failed` сразу после обновления | Образ не пересобран: `up -d --build` |
| Judge0: `Internal Error`, `/box/script.py` | Сервер на cgroup v2 — шаг 3 |
| `permission denied ... docker.sock` | Нет прав на docker: `sudo` или группа `docker` (шаг 4) |

Логи Judge0 при старте выводят переменные окружения, в том числе пароли и
токен: не пересылайте их целиком.

## Бэкапы

Регулярные бэкапы пока не настроены (запланированы после хакатона, см.
корневой README). Данные лежат в томах `zebra_pgdata` (база), `zebra_s3data`
(файлы) и `zebra_caddy_data` (сертификаты). Ручной дамп базы:

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup-$(date +%F).sql
```
