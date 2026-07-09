# Service to register DOI's

## Install

```bash
uv pip install s2rdoi
```

## Usage

```bash
s2rdoi public-doi --input-xml path/to/file.xml --output-xml path/to/out.xml --publisher "YOUR Publisher Name" --username USERNAME --password PASSWORD --prefix PREFIX --test
```

At the moment only Book Interchangable Tag Set (BITS) is supported.
