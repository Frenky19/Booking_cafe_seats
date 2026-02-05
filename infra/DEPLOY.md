# Production Deploy (server)

Assumes domain `yamdb.ru` and host port `8004`.

1. Clone repo:
```
git clone <repository_url> /root/booking_service
```

2. Create `.env` from example and fill secrets:
```
cd /root/booking_service/infra
cp .env.example .env
```

3. Build + run:
```
docker compose -f /root/booking_service/infra/docker-compose.production.yml build
docker compose -f /root/booking_service/infra/docker-compose.production.yml up -d
docker compose -f /root/booking_service/infra/docker-compose.production.yml exec -T app alembic upgrade head
```

4. Nginx:
```
cp /root/booking_service/infra/nginx.yamdb.conf /etc/nginx/sites-available/booking_service
ln -s /etc/nginx/sites-available/booking_service /etc/nginx/sites-enabled/booking_service
nginx -t
systemctl reload nginx
```

5. HTTPS:
```
certbot --nginx -d yamdb.ru -d www.yamdb.ru
```
