# Deployment

The foundation includes Docker artifacts for Linux container deployment.

## Build

```bash
docker compose build
```

## Run

```bash
docker compose run --rm new-latex-app --help
```

## Notes

- TeX Live is installed in the image for future PDF compilation.
- Runtime input/output should be streamed through the presentation layer.
- Do not mount persistent user-document directories into the container for processing.
- Keep `.env` outside the image and pass environment variables at runtime.
