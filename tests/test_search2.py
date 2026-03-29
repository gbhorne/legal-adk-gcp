from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.client_options import ClientOptions

client = discoveryengine.SearchServiceClient(
    client_options=ClientOptions(api_endpoint='us-discoveryengine.googleapis.com')
)
serving_config = (
    'projects/1073947050575/locations/us'
    '/collections/default_collection'
    '/engines/legal-search-app_1774806682231'
    '/servingConfigs/default_serving_config'
)

for query in ['non-compete', 'contract', 'employment', 'negligence']:
    response = client.search(discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=2,
    ))
    results = list(response.results)
    print('Query [' + query + ']: ' + str(len(results)) + ' results')
    for r in results:
        s = dict(r.document.struct_data)
        print('  - ' + str(s.get('case_name')) + ' | ' + str(s.get('court_id')) + ' | ' + str(s.get('date_filed')))
    print()
