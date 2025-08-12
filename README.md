## HERMES GitHub and GitLab Plugin for Metadata Extraction
> This plugin automatically harvests metadata from GitHub and GitLab repositories.
> The extraction follows the **[CodeMeta](https://codemeta.github.io/)** standard to ensure compatibility and interoperability with other metadata tools and formats.
## Automatically Extracted Metadata
> The following metadata fields are extracted automatically:  
> *(Listed in alphabetical order)*
- **codeRepository**: Link to the repository where the un-compiled, human readable code and related code is located.  
- **contributor**: A secondary contributor to the CreativeWork or Event.  
- **copyrightHolder**: The party holding the legal copyright to the CreativeWork.  
- **dateCreated**: The date on which the CreativeWork was created or the item was added to a DataFeed.  
- **dateModified**: The date on which the CreativeWork was most recently modified or when the item's entry was modified within a DataFeed.  
- **datePublished**: Date of first broadcast/publication.  
- **description**: A description of the item.  
- **downloadUrl**: If the file can be downloaded, URL to download the binary.  
- **identifier**: The identifier property represents any kind of identifier for any kind of Thing, such as ISBNs, GTIN codes, UUIDs etc. Schema.org provides dedicated properties for representing many of these, either as textual strings or as URL (URI) links.  
- **issueTracker**: Link to software bug reporting or issue tracking system.  
- **keywords**: Keywords or tags used to describe this content. Multiple entries in a keywords list are typically delimited by commas.  
- **license**: A license document that applies to this content, typically indicated by URL.  
- **name**: The name of the item (software, Organization).  
- **programmingLanguage**: The computer programming language.  
- **readme**: Link to software Readme file.  
- **url**: URL of the item.

## Run Locally
> Clone the HERMES project _(feature branch)_
```bash
  git clone --branch feature/276-harvesting-metadata-from-a-provided-repository-URL https://github.com/Aidajafarbigloo/hermes.git
```
> Go to the project directory
```bash
  cd hermes
```
> Install HERMES dependencies
```bash
pip install .
```
> Clone the plugin repository
```bash
git clone https://github.com/softwarepub/hermes-plugin-github-gitlab.git
```
> Go to the plugin directory
```bash
cd hermes-plugin-github-gitlab
```
> Install plugin dependencies
```bash
pip install .
```
> Configure HERMES

Ensure you have a `hermes.toml` file in your working directory.

Edit the file to include or remove sources as needed:

```bash
sources = ["cff", "codemeta", "githublab"]
```
> Verify Installation
```bash
hermes --help
```
If you see the help message, HERMES is installed correctly.

> Harvest Metadata

From a local repository:
```bash
hermes harvest
```

From a remote repository: _(This extracts metadata from the defined sources for the specified repository.)_
```bash
hermes harvest --path <URL>
```
