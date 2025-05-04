# letoii
![“The power to destroy a thing is the absolute control over it”](./images/logo_100.png)

“But it was all based on the spice, a substance whose value, though enormous, kept increasing.”
— *Leto II, God Emperor of Dune*

## Overview
Letoii is a project that includes a web scraper component built with Python. The scraper is containerized for easy deployment and consistent execution across different environments.

## Components

### Scraper
The scraper is a Python application that collects data from web sources. It's containerized using a Fedora-based Python 3.13 image.

#### Features
- Built on Python 3.13
- Containerized for consistent execution
- Multi-architecture support (ARM64 and AMD64)

#### Development

To run the scraper locally:

1. Navigate to the scraper directory:
   ```
   cd src/scraper
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the scraper:
   ```
   python main.py
   ```

#### Container Build

The scraper can be built as a container using the provided Containerfile:

```bash
docker build -t letoii-scraper -f build/scraper.Containerfile .
```

To run the container:

```bash
docker run letoii-scraper
```

## CI/CD

This project uses GitHub Actions for continuous integration and deployment:

- Automatic container builds on code changes
- Multi-architecture builds (ARM64 and AMD64)
- Container images published to GitHub Container Registry

### Container Images

The latest container images are available at:
```
ghcr.io/kalenpeterson/letoii/scraper:latest
```

You can pull specific architectures with:
```bash
# For AMD64 (x86)
docker pull --platform linux/amd64 ghcr.io/kalenpeterson/letoii/scraper:latest

# For ARM64
docker pull --platform linux/arm64 ghcr.io/kalenpeterson/letoii/scraper:latest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license information here]
