
# Obsidian API Python Wrapper

This is a simple Python wrapper of the [Obsidian Local REST API](https://coddingtonbear.github.io/obsidian-local-rest-api/).

## Installation

1. Download the package:
   - git:
   `git clone https://github.com/evelynkyl/obsidian_python_api.git`
   - or wget:
   `wget --no-check-certificate --content-disposition https://github.com/evelynkyl/obsidian_python_api/archive/refs/heads/main.zip`
   - or curl:
   `curl -LJO https://github.com/evelynkyl/obsidian_python_api/archive/refs/heads/main.zip`
2. Install:
`sudo python setup.py install`
Or
`pip install git+https://github.com/evelynkyl/obsidian_python_api.git`

## Usage

```python
API_URL, API_Key = 'demo_url', 'demo_api_key'
Obsidian = ObsidianFiles(API_URL, API_Key)

# Get the content of the currently open file on Obsidian
active_content = Obsidian._get_active_file_content()

# Search your vault with a JSON / dataview query
request_body = '''TABLE
  time-played AS "Time Played",
  length AS "Length",
  rating AS "Rating"
FROM #game
SORT rating DESC'''

files_from_query = Obsidian._search_with_query(request_body)
files_from_query
```
