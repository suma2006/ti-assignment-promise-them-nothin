import asyncio
import time
import httpx
import sys
from collections import defaultdict

API_URL = "http://localhost:8080/api/v1/ping"

class RequestResult:
    def __init__(self, send_time: float, status_code: int, node_id: str):
        self.send_time = send_time
        self.status_code = status_code
        self.node_id = node_id

async def fire_request(client: httpx.AsyncClient, customer_id: str) -> RequestResult:
    send_time = time.time()
    try:
        response = await client.get(API_URL, headers={"X-Customer-Id": customer_id})
        return RequestResult(send_time, response.status_code, response.headers.get("x-node-id", "unknown"))
    except Exception as e:
        return RequestResult(send_time, 0, str(e))

async def drive_burst(client: httpx.AsyncClient, customer_id: str, count: int):
    tasks = [asyncio.create_task(fire_request(client, customer_id)) for _ in range(count)]
    return await asyncio.gather(*tasks)

async def main():
    limits = httpx.Limits(max_connections=5000, max_keepalive_connections=1000)
    async with httpx.AsyncClient(limits=limits, timeout=10.0) as client:
        now = time.time()
        next_boundary = (now // 60 + 1) * 60
        wait_time = (next_boundary - 2.0) - now
        if wait_time < 0:
            next_boundary += 60
            wait_time = (next_boundary - 2.0) - now
            
        print(f"Waiting {wait_time:.2f}s for boundary {next_boundary}")
        await asyncio.sleep(wait_time)
        
        t1 = time.time()
        res1 = await drive_burst(client, "cust-growth-1", 300)
        t2 = time.time()
        
        wait_2 = (next_boundary + 1.0) - time.time()
        if wait_2 > 0:
            await asyncio.sleep(wait_2)
            
        t3 = time.time()
        res2 = await drive_burst(client, "cust-growth-1", 300)
        t4 = time.time()
        
        all_res = res1 + res2
        print(f"Computed boundary: {next_boundary}")
        print(f"res1 start: {t1}, res1 end: {t2}, sent: {len(res1)}")
        print(f"res2 start: {t3}, res2 end: {t4}, sent: {len(res2)}")
        
        nodes1 = defaultdict(int)
        codes1 = defaultdict(int)
        for r in res1:
            nodes1[r.node_id] += 1
            codes1[r.status_code] += 1
            
        nodes2 = defaultdict(int)
        codes2 = defaultdict(int)
        for r in res2:
            nodes2[r.node_id] += 1
            codes2[r.status_code] += 1
            
        print(f"res1 codes: {dict(codes1)}")
        print(f"res1 nodes: {dict(nodes1)}")
        
        print(f"res2 codes: {dict(codes2)}")
        print(f"res2 nodes: {dict(nodes2)}")

if __name__ == '__main__':
    asyncio.run(main())
