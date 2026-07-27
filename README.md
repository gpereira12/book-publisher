# 📚 Book Publisher

A Python-based book publishing automation system that transforms text inputs into professionally formatted PDF books — including cover design, typesetting, and branding.

## Features

- **Automated Diagramação** — Converts raw text into structured HTML and then into print-ready PDFs
- **Cover Design** — Branding system with customizable cover templates
- **Multi-book Support** — Manage multiple book projects simultaneously
- **Playwright-powered PDF generation** — High-fidelity rendering

## Project Structure

```
.
├── src/                  # Core source code
├── inputs/               # Raw book content (per book folder)
├── branding_system/      # Cover templates, fonts, and visual identity
├── resources/            # Shared assets (logos, etc.)
├── main.py               # Entry point
├── inspect_pdf.py        # PDF inspection utility
└── requirements.txt      # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.10+
- [Playwright](https://playwright.dev/python/)

### Installation

```bash
# Clone the repository
git clone https://github.com/gabrielpereira/book-publisher.git
cd book-publisher

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Usage

```bash
python main.py
```

## License

MIT
