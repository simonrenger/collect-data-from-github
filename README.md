# collect-data-from-github
A little tool collection to help you collecting data from GitHub for research. This tool is based on my blog post: [Systematic review of repositories on GitHub with python (Game Dev Style)](https://simonrenger.de/posts/systematic_review_on_github/)

## Install

```
$ git clone https://github.com/simonrenger/collect-data-from-github.git
$  pip install PyGithub
$ pip install pandas
```

## How to use tool `collect.py` 

Call the help function:

```bash
python collect.py --help
```

You need to provide a `config.json` file:

| Field      | Type          | Optional | Description                                                  |
| ---------- | ------------- | -------- | ------------------------------------------------------------ |
| token      | string        | Yes      | If present it should contain a valid GitHub Token. You can obtain it here: [Settings/Token](https://github.com/settings/tokens).  **Scopes:** `repos`. **If not provided `--token {TOKEN}` needs to be used** |
| readme_dir | string        | Yes      | If present the tool will automatically download GitHub readme files into this location. |
| output     | string        | Yes      | If present the tool will store the found data in this location. **Default:** `./` |
| format     | string        | yes      | If present it determines the output format. **Valid input: `JSON`, `CSV`, `HTML`, `MARKDOWN`**. **Default: `CSV`** |
| criteria   | object        | No       | Must contain a entry called `time` with the fields `min` or `max` |
| terms      | array<string> | No       | List of search terms in accordance to the GitHub Syntax API: [Understanding the search syntax](https://docs.github.com/en/search-github/getting-started-with-searching-on-github/understanding-the-search-syntax) |
| attrs      | array<string> | No       | List of attributes from the [repo GitHub REST API object](https://docs.github.com/en/rest/reference/repos) |

> **Note:** There is a sample config in the `samples` folder

The previous command will give you some ideas on how to run it. But there is a faster way:

```bash
python collect.py config.json
```

And if you want to pass a token along:

```bash
python collect.py --token my_token config.json 
```

## Roadmap

[] Add more criteria to filter repos on e.g. Languages
