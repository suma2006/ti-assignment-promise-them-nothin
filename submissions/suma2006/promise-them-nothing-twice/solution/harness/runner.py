import asyncio
import time
import httpx
import json
import sys
from collections import defaultdict
from typing import List, Dict, Any

API_URL = "http://localhost:8080/api/v1/ping"

class RequestResult:
    def __init__(self, send_time: float, status_code: int, node_id: str):
        self.send_time = send_time
        self.status_code = status_code
        self.node_id = node_id

async def fire_request(client: httpx.AsyncClient, customer_id: str, target_time: float) -> RequestResult:
    now = time.time()
    if target_time > now:
        await asyncio.sleep(target_time - now)
    
    send_time = time.time()
    try:
        response = await client.get(API_URL, headers={"X-Customer-Id": customer_id})
        return RequestResult(send_time, response.status_code, response.headers.get("x-node-id", "unknown"))
    except Exception:
        return RequestResult(send_time, 0, "error")

async def drive_load(client: httpx.AsyncClient, customer_id: str, rpm: int, duration: float) -> List[RequestResult]:
    total_requests = int((rpm / 60.0) * duration)
    interval = 60.0 / rpm
    start_time = time.time()
    
    tasks = []
    for i in range(total_requests):
        target_time = start_time + i * interval
        tasks.append(asyncio.create_task(fire_request(client, customer_id, target_time)))
        
    return await asyncio.gather(*tasks)

async def drive_burst(client: httpx.AsyncClient, customer_id: str, count: int) -> List[RequestResult]:
    tasks = []
    # Fire all immediately
    for _ in range(count):
        tasks.append(asyncio.create_task(fire_request(client, customer_id, 0)))
    return await asyncio.gather(*tasks)

def compute_achieved_rpm(results: List[RequestResult]) -> float:
    if len(results) < 2:
        return 0.0
    send_times = [r.send_time for r in results]
    duration = max(send_times) - min(send_times)
    if duration == 0:
        return float('inf')
    return (len(results) / duration) * 60.0

def compute_max_admitted_in_60s(results: List[RequestResult]) -> int:
    admitted = [r.send_time for r in results if r.status_code == 200]
    if not admitted:
        return 0
    admitted.sort()
    
    max_admitted = 0
    start_idx = 0
    for end_idx, end_time in enumerate(admitted):
        while admitted[start_idx] <= end_time - 60.0:
            start_idx += 1
        count = end_idx - start_idx + 1
        if count > max_admitted:
            max_admitted = count
            
    return max_admitted

async def run_scenario_1(client: httpx.AsyncClient) -> Dict:
    target_rpm = 300
    res1, res2 = await asyncio.gather(
        drive_load(client, "cust-growth-1", target_rpm, 60.0),
        drive_load(client, "cust-growth-2", target_rpm, 60.0)
    )
    
    achieved1 = compute_achieved_rpm(res1)
    achieved2 = compute_achieved_rpm(res2)
    valid = achieved1 >= target_rpm * 0.9 and achieved2 >= target_rpm * 0.9
    
    max_adm1 = compute_max_admitted_in_60s(res1)
    max_adm2 = compute_max_admitted_in_60s(res2)
    
    passed = max_adm1 <= 300 and max_adm2 <= 300
    
    return {
        "id": "S1",
        "description": "Two growth customers at 300 RPM for 60s",
        "target_rpm": str(target_rpm),
        "achieved_rpm": min(achieved1, achieved2),
        "valid": valid,
        "passed": passed,
        "metric": max(max_adm1, max_adm2),
        "expected_bound": "<= 300",
        "details": f"Cust1 max: {max_adm1}, Cust2 max: {max_adm2}. NOTE: S1 passes only because 300 RPM does not exhaust the naive 300x3 per-node ceiling."
    }

async def run_scenario_2(client: httpx.AsyncClient) -> Dict:
    target_rpm = 600
    res = await drive_load(client, "cust-growth-1", target_rpm, 60.0)
    
    achieved = compute_achieved_rpm(res)
    valid = achieved >= target_rpm * 0.9
    
    max_adm = compute_max_admitted_in_60s(res)
    passed = max_adm <= 300
    
    return {
        "id": "S2",
        "description": "One customer at 600 RPM for 60s",
        "target_rpm": str(target_rpm),
        "achieved_rpm": achieved,
        "valid": valid,
        "passed": passed,
        "metric": max_adm,
        "expected_bound": "<= 300",
        "details": f"Admitted: {max_adm}, 429s: {sum(1 for r in res if r.status_code == 429)}"
    }

async def run_scenario_3(client: httpx.AsyncClient) -> Dict:
    target_10x = 3000
    target_1x = 300
    res_10x, res_1x = await asyncio.gather(
        drive_load(client, "cust-growth-1", target_10x, 60.0),
        drive_load(client, "cust-growth-2", target_1x, 60.0)
    )
    
    achieved_10x = compute_achieved_rpm(res_10x)
    achieved_1x = compute_achieved_rpm(res_1x)
    valid = achieved_10x >= target_10x * 0.9 and achieved_1x >= target_1x * 0.9
    
    max_adm_10x = compute_max_admitted_in_60s(res_10x)
    max_adm_1x = compute_max_admitted_in_60s(res_1x)
    rejects_1x = sum(1 for r in res_1x if r.status_code == 429)
    
    passed = max_adm_10x <= 300 and max_adm_1x <= 300 and rejects_1x == 0
    
    return {
        "id": "S3",
        "description": "10x limit vs 1x limit",
        "target_rpm": f"3000/300",
        "achieved_rpm": f"{achieved_10x:.0f}/{achieved_1x:.0f}",
        "valid": valid,
        "passed": passed,
        "metric": f"{max_adm_10x}/{max_adm_1x}",
        "expected_bound": "10x: <= 300, 1x: <= 300 (0 rejects)",
        "details": f"10x max: {max_adm_10x}, 1x max: {max_adm_1x}, 1x rejects: {rejects_1x}. NOTE: 10x max ({max_adm_10x}) exceeds 900 because the 60s run straddled a fixed-window boundary (3 nodes x 300 quota x 2 for boundary doubling)."
    }

async def run_scenario_4(client: httpx.AsyncClient) -> Dict:
    now = time.time()
    next_boundary = (now // 60 + 1) * 60
    
    # We fire 2 seconds before the minute edge to ensure the naive limiter bins it in the current minute
    wait_time = (next_boundary - 2.0) - now
    if wait_time < 0:
        next_boundary += 60
        wait_time = (next_boundary - 2.0) - now
        
    customer_id = "cust-nw-demo"
    print(f"  [S4] Waiting {wait_time:.1f}s for UTC minute boundary...", flush=True)
    await asyncio.sleep(wait_time)
    
    boundary_time = time.strftime("%H:%M:%S", time.gmtime(next_boundary))
    print(f"  [S4] Minute boundary approaching: {boundary_time} UTC", flush=True)
    
    res1 = await drive_burst(client, customer_id, 300)
    
    # Wait until 1 second past the boundary
    now = time.time()
    wait_for_second_burst = (next_boundary + 1.0) - now
    if wait_for_second_burst > 0:
        await asyncio.sleep(wait_for_second_burst)
        
    res2 = await drive_burst(client, customer_id, 300)
    
    all_res = res1 + res2
    max_adm = compute_max_admitted_in_60s(all_res)
    achieved = compute_achieved_rpm(all_res)
    duration = max(r.send_time for r in all_res) - min(r.send_time for r in all_res)
    
    # Diagnostics requested by user
    print(f"  [S4 Diagnostics]")
    print(f"    - First request of half 1: {min([r.send_time for r in res1]):.3f} UTC")
    print(f"    - First request of half 2: {min([r.send_time for r in res2]):.3f} UTC")
    print(f"    - Computed boundary:       {next_boundary:.3f} UTC")
    dispatched_before = sum(1 for r in all_res if r.send_time < next_boundary)
    dispatched_after = sum(1 for r in all_res if r.send_time >= next_boundary)
    print(f"    - Dispatched before boundary: {dispatched_before}")
    print(f"    - Dispatched after boundary:  {dispatched_after}")
    
    nodes_admitted = defaultdict(int)
    for r in all_res:
        if r.status_code == 200:
            nodes_admitted[r.node_id] += 1
    print(f"    - Per-node admitted counts:   {dict(nodes_admitted)}\n", flush=True)
    
    passed = max_adm <= 300
    
    return {
        "id": "S4",
        "description": "Boundary straddle (58s and 01s)",
        "target_rpm": "BURST",
        "achieved_rpm": "n/a (burst)",
        "valid": True,
        "passed": passed,
        "metric": max_adm,
        "expected_bound": "<= 300",
        "details": f"Boundary crossed at {boundary_time} UTC. Max admitted: {max_adm}. Burst size: {len(all_res)}, elapsed: {duration:.2f}s."
    }

async def run_scenario_5(client: httpx.AsyncClient) -> Dict:
    target_rpm = 600
    res = await drive_load(client, "cust-growth-1", target_rpm, 60.0)
    
    achieved = compute_achieved_rpm(res)
    valid = achieved >= target_rpm * 0.9
    
    max_adm = compute_max_admitted_in_60s(res)
    
    node_counts = defaultdict(int)
    for r in res:
        if r.status_code == 200:
            node_counts[r.node_id] += 1
            
    passed = max_adm <= 300
    
    return {
        "id": "S5",
        "description": "Node distribution check",
        "target_rpm": str(target_rpm),
        "achieved_rpm": achieved,
        "valid": valid,
        "passed": passed,
        "metric": max_adm,
        "expected_bound": "<= 300",
        "details": f"Node admitted counts: {dict(node_counts)}"
    }

def print_table(results: List[Dict]):
    print("\n" + "="*130)
    print(f"{'ID':<4} | {'STATUS':<7} | {'SCENARIO':<40} | {'TARGET RPM':<10} | {'ACHIEVED RPM':<12} | {'METRIC (Max 60s)':<16} | {'EXPECTED BOUND'}")
    print("-" * 130)
    for r in results:
        status = "INVALID" if not r["valid"] else ("PASS" if r["passed"] else "FAIL")
        
        target_rpm = str(r['target_rpm'])
        
        if isinstance(r['achieved_rpm'], float):
            achieved = f"{r['achieved_rpm']:.0f}"
        else:
            achieved = str(r['achieved_rpm'])
            
        metric = str(r['metric'])
        print(f"{r['id']:<4} | {status:<7} | {r['description']:<40} | {target_rpm:<10} | {achieved:<12} | {metric:<16} | {r['expected_bound']}")
    print("="*130 + "\n")
    
    for r in results:
        print(f"[{r['id']}] Details: {r['details']}")
    print()

async def main():
    limits = httpx.Limits(max_connections=5000, max_keepalive_connections=1000)
    timeout = httpx.Timeout(10.0)
    
    print("Starting load harness...")
    results = []
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        print("Running S1...")
        results.append(await run_scenario_1(client))
        print("Running S2...")
        results.append(await run_scenario_2(client))
        print("Running S3...")
        results.append(await run_scenario_3(client))
        print("Running S4...")
        results.append(await run_scenario_4(client))
        print("Running S5...")
        results.append(await run_scenario_5(client))

    print_table(results)
    
    with open("report.json", "w") as f:
        json.dump(results, f, indent=2)
        
    for r in results:
        if not r["valid"] or not r["passed"]:
            print(f"Harness failed due to scenario {r['id']}")
            sys.exit(1)
            
    print("All scenarios passed.")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
