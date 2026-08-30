import requests
import time

url = "http://localhost:8080/api/v1/ping"
headers = {"X-Customer-Id": "cust-nw-demo"}

status_counts = {}
node_counts = {}

start = time.time()
for _ in range(400):
    resp = requests.get(url, headers=headers)
    status = resp.status_code
    node = resp.headers.get("x-node-id", "unknown")
    
    status_counts[status] = status_counts.get(status, 0) + 1
    node_counts[node] = node_counts.get(node, 0) + 1

end = time.time()

print(f"Time: {end - start:.2f}s")
print(f"Status codes: {status_counts}")
print(f"Node counts: {node_counts}")
