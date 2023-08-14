## Release process

To release a new version of cad_viewer_widget on PyPI:

1. Either clean working folder

   ```shell
   make clean
   ```

   or prepare for a new release

   ```shell
   make prepare
   ```

2. Bump version

   ```shell
   make bump part=[major|minor|patch|build|release]
   ```

3. Make distribution

   ```shell
   make dist
   ```

4. Update docs

   ```shell
   make docs
   ```

5. Commit and tag release

   ```shell
   make release
   ```

6. Upload to pypi

   ```shell
   make upload
   ```

7. Upload javascript package to npm

   ```shell
   make upload_js
   ```

8.

   ```shell
   # Set github token
   make create-release   
   ```

