import json
import urllib.request
import urllib.error
import sys

# Load token from rclone.conf
token_str = None
with open('/workspace/data/rclone/rclone.conf', 'r') as f:
    for line in f:
        if line.strip().startswith('token ='):
            token_str = line.strip().split('token =')[1].strip()
            break

if not token_str:
    print("No token found in rclone.conf")
    sys.exit(1)

token_data = json.loads(token_str)
access_token = token_data.get('access_token')

headers = {'Authorization': f'Bearer {access_token}'}

def query_api(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error for {url}: {e.code} - {e.read().decode()}")
        return None
    except Exception as e:
        print(f"Error for {url}: {e}")
        return None

print("=== 1. DEEP SEARCHING FOR REMOTE ITEMS (SHORTCUTS) ===")
# Search all items in OneDrive
search_url = 'https://graph.microsoft.com/v1.0/me/drive/root/search(q=\'\')'
res = query_api(search_url)
if res:
    items = res.get('value', [])
    print(f"Total search items found: {len(items)}")
    remote_count = 0
    for item in items:
        if 'remoteItem' in item:
            remote_count += 1
            print(f"- Remote Item Found: {item.get('name')}")
            ri = item['remoteItem']
            print(f"  Target: {ri.get('name')}")
            print(f"  ID: {item.get('id')}")
    if remote_count == 0:
        print("No items with remoteItem facet found in deep search.")

print("\n=== 2. CHECKING SUBFOLDERS OF ROOT FOR SHORTCUTS ===")
# Let's inspect subfolders like Documents/ children
root_res = query_api('https://graph.microsoft.com/v1.0/me/drive/root/children')
if root_res:
    for item in root_res.get('value', []):
        if 'folder' in item:
            name = item.get('name')
            item_id = item.get('id')
            sub_res = query_api(f'https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/children')
            if sub_res:
                sub_items = sub_res.get('value', [])
                for sub in sub_items:
                    if 'remoteItem' in sub:
                        print(f"- Remote Item in {name}: {sub.get('name')}")

print("\n=== 3. CHECKING FOLLOWED SITES ===")
followed_url = 'https://graph.microsoft.com/v1.0/sites?select=id,name,webUrl'
followed_res = query_api(followed_url)
if followed_res:
    sites = followed_res.get('value', [])
    print(f"Total sites found: {len(sites)}")
    for site in sites[:10]:
        print(f"- Site: {site.get('name')} ({site.get('webUrl')})")
