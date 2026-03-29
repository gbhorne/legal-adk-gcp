import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.client_options import ClientOptions
from config import config

def test_search(query):
    client = discoveryengine.SearchServiceClient(
        client_options=ClientOptions(api_endpoint='us-discoveryengine.googleapis.com')
    )
    serving_config = (
        f'projects/1073947050575/locations/us'
        f'/collections/default_collection'
        f'/dataStores/{config.SEARCH_DATASTORE_ID}'
        f'/servingConfigs/default_config'
    )
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=5,
    )
    response = client.search(request)
    results = list(response.results)
    print(f"Query: '{query}'")
    print(f"Results: {len(results)}")
    print()
    for i, result in enumerate(results):
        struct = dict(result.document.struct_data)
        print(f"  [{i+1}] {struct.get('case_name')} ({struct.get('court_id')}, {struct.get('date_filed')})")
        print(f"       {struct.get('text', '')[:120]}")
        print()

if __name__ == "__main__":
    test_search("non-compete agreement enforceability Georgia")
    test_search("contract termination clause")

