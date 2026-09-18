import requests

def main():
    print("=" * 60)
    print("DEX HUNTER - Phase 1 Scanner")
    print("=" * 60)
    
    try:
        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        print(f"Connecting to: {url}")
        
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print(f"Type of data: {type(data)}")
        print(f"Number of tokens: {len(data)}")
        
        print("-" * 60)
        print("First 10 tokens:")
        print("-" * 60)
        
        for i, item in enumerate(data[:10], 1):
            chain = item.get("chainId", "?")
            address = item.get("tokenAddress", "?")
            print(f"{i}. Chain: {chain} | Address: {address}")
        
        print("=" * 60)
        print("SUCCESS - Scanner completed")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}")
        print(f"Message: {e}")
        raise

if __name__ == '__main__':
    main()
