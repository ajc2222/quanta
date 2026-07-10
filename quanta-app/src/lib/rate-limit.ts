import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL!,
  token: process.env.UPSTASH_REDIS_REST_TOKEN!,
});

export async function checkRateLimit(
  identifier: string,
  maxRequests: number = 60,
  windowSeconds: number = 60,
): Promise<{ allowed: boolean; remaining: number }> {
  const key = `ratelimit:${identifier}`;
  const current = await redis.incr(key);
  if (current === 1) await redis.expire(key, windowSeconds);
  const ttl = await redis.ttl(key);
  return {
    allowed: current <= maxRequests,
    remaining: Math.max(0, maxRequests - current),
  };
}
