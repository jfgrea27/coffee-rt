FROM redis:7-alpine

ENV REDIS_INIT=${REDIS_INIT:-true}

COPY .dev/redis-init/init.sh /init.sh
RUN chmod +x /init.sh

ENTRYPOINT ["/init.sh"]
