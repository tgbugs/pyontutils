# Intro
This folder contains documents for vocabulary to be integrated into the NIF-Ontology
prior to their conversion into ttl format for inclusion in the NIF-Ontology repository.

# Process
When adding source files (csv, xlsx, ttl, etc.) for review and integration,
[fork tgbugs/pyontutils](https://github.com/tgbugs/pyontutils/fork),
add a folder for your files/notes and submit a pull requests.
Any additional files related to that particular set of terms or that project
should be added to that folder as well.

For example, if I want to integrate a vocabulary related to 2-photon calcium
imaging I would (from the folder that contains this readme)
```bash
mkdir calcium-imaging
cp -a path/to/my/terms-doc calcium-imaging/
git add calcium-imaging/terms-doc
git commit
git push
```
and then submit a [pull request](https://github.com/tgbugs/pyontutils/compare?expand=1).

With these files as a starting point we will then have a record of the process by which
the new terms are considered and ultimately added to the NIF-Ontology.

# Integration from an existing git repo
In the folder please include a README.md that has a link to the repo and
any other relevant links.
