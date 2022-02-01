
seqr
====
![Unit Tests](https://github.com/populationgenomics/seqr/workflows/Unit%20Tests/badge.svg?branch=master) | ![Local Install Tests](https://github.com/populationgenomics/seqr/workflows/local%20install%20tests/badge.svg?branch=master)

seqr is a web-based tool for rare disease genomics.

## Contributing to seqr

(Note: section inspired by, and some text copied from, [GATK](https://github.com/broadinstitute/gatk#contribute))

We welcome all contributions to seqr. 
Code should be contributed via GitHub pull requests against the main seqr repository.

If you’d like to report a bug but don’t have time to fix it, you can submit a
[GitHub issue](https://github.com/broadinstitute/seqr/issues/new?assignees=&labels=bug&template=bug_report.md&title=)

For larger features, feel free to discuss your ideas or approach in our 
[discussion forum](https://github.com/broadinstitute/seqr/discussions)

To contribute code:

* Submit a GitHub pull request against the master branch.
* Break your work into small, single-purpose patches whenever possible. 
However, do not break apart features to the point that they are not functional 
(i.e. updates that require changes to both front end and backend code should be submitted as a single change)
* For larger features, add a detailed description to the pull request to explain the changes and your approach
* Make sure that your code passes all our tests and style linting
* Add unit tests for all new python code you've written

We tend to do fairly close readings of pull requests, and you may get a lot of comments.

Thank you for getting involved!

## Development

At the CPG, we don't include the web bundle in the repository anymore, this means you'll need to build the UI before you develop first.

Build UI and link build files back to `static/`:

```bash
cd ui/
npm install
npm run build
ln dist/app* ../static
cd ..
```

Start Python server:

```bash
gunicorn -c deploy/docker/seqr/config/gunicorn_config.py wsgi:application
```

### Developing UI

If you're developing UI, you can run a hot-reload UI server. You'll need to start the Python server first (using gunicorn), then run:

```bash
cd ui/
npm run start
```

Then visit https://localhost:3000 in your browser to access the hot-reloadable version of seqr. All requests are proxied back to to Python backend.

### Common errors

- `Error occured while trying to proxy to: localhost:3000`: You didn't start the Python backend server.
- `TemplateDoesNotExist at / app.html`: then it might say something like: `/Users/${USER}/source/seqr/ui/dist/app.html (Source does not exist)`, you'll need to make sure the `app.html` file is available in `ui/dist/`.
