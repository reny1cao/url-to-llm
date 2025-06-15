# Content Extraction and Formatting Logic

## Overview

The system uses a sophisticated multi-stage approach to extract, format, and display web content. Here's how it works:

## 1. Content Extraction (Backend)

### Primary Extraction: Trafilatura
```python
# backend/app/crawler/documentation_crawler.py
extracted = trafilatura.extract(
    html_content,
    include_comments=False,      # Skip HTML comments
    include_tables=True,         # Keep tables for documentation
    include_images=False,        # Text-only extraction
    include_links=True,          # Preserve link context
    output_format='markdown'     # Convert to Markdown
)
```

**Trafilatura Features:**
- State-of-the-art web content extraction
- Removes navigation, ads, footers automatically
- Preserves document structure (headings, lists, code blocks)
- Converts HTML to clean Markdown format
- Handles various HTML structures intelligently

### Fallback Extraction
If Trafilatura fails:
```python
# Basic text extraction with BeautifulSoup
soup.get_text(strip=True, separator=' ')[:10000]
```

### Metadata Extraction
```python
# Title extraction priority:
1. <title> tag
2. <h1> tag
3. og:title meta tag

# Description extraction priority:
1. <meta name="description">
2. <meta property="og:description">
```

## 2. Content Storage

### Dual Format Storage
Each page is stored in two formats:

1. **Original HTML** (`/pages{path}/index.html`)
   - Complete original HTML
   - Preserves all formatting and structure
   - Used for full-fidelity display if needed

2. **Extracted Markdown** (`/pages{path}/content.md`)
   - Clean, readable content
   - Trafilatura-extracted text
   - Optimized for documentation display

### Database Storage
```sql
-- Pages table stores:
- extracted_text: First 10KB for full-text search
- content_hash: SHA256 for change detection
- html_storage_key: S3 path to HTML
- markdown_storage_key: S3 path to Markdown
```

## 3. Content Serving (API)

### Flexible Format Support
```python
# API endpoint: /docs/{host}/page/{path}?format={format}
- format=html: Returns original HTML
- format=markdown: Returns extracted Markdown
- format=json: Returns page metadata
```

### Response Processing
```python
# When format=markdown is requested:
1. Fetch Markdown content from S3
2. Return as text/markdown with UTF-8 encoding
3. Include cache headers for performance
```

## 4. Frontend Display

### Markdown Rendering Pipeline
```typescript
// Using react-markdown with custom components
<ReactMarkdown
  components={{
    // Syntax highlighting for code blocks
    code({ className, children }) {
      return (
        <SyntaxHighlighter
          style={darkMode ? oneDark : oneLight}
          language={detectLanguage(className)}
        >
          {children}
        </SyntaxHighlighter>
      )
    },
    // External link handling
    a({ href, children }) {
      const isExternal = href?.startsWith('http')
      return (
        <a
          href={href}
          target={isExternal ? '_blank' : undefined}
          rel={isExternal ? 'noopener noreferrer' : undefined}
        >
          {children}
        </a>
      )
    }
  }}
>
  {content.content}
</ReactMarkdown>
```

### Styling with Tailwind Typography
```html
<div className="prose prose-lg dark:prose-invert max-w-none">
  <!-- Rendered Markdown -->
</div>
```

**Typography Features:**
- Beautiful default styling for all elements
- Dark mode support
- Responsive font sizes
- Proper spacing and line heights
- Code block styling

## 5. Manifest Generation

### LLM-Optimized Format
For AI consumption, content is formatted differently:

```markdown
# Page Summaries

### 1. Page Title
- **URL:** `https://site.com/page`
- **Description:** Meta description
- **Size:** 12,345 bytes
- **Content Hash:** `abc123...`

**Content Preview:**
```
First 2-3 meaningful paragraphs
or up to 1000 characters...

[Content continues...]
```
```

**Manifest Logic:**
1. Groups pages by structure
2. Includes first 20 pages in detail
3. Provides content previews (not full content)
4. Adds metadata and statistics
5. Optimized for LLM understanding

## 6. Search Indexing

### Full-Text Search
```sql
-- PostgreSQL full-text search
- extracted_text: First 10KB indexed
- search_vector: tsvector for fast searching
- Supports highlighting with ts_headline
```

## Summary of Formatting Philosophy

1. **Extraction**: Use best-in-class tools (Trafilatura) for clean content
2. **Storage**: Keep both original and extracted formats
3. **Flexibility**: Serve content in multiple formats as needed
4. **Display**: Beautiful typography with syntax highlighting
5. **Search**: Full-text indexing of extracted content
6. **AI-Ready**: Special manifest format for LLM consumption

The system prioritizes:
- **Readability**: Clean, well-formatted content
- **Accuracy**: Faithful representation of original
- **Performance**: Cached and optimized delivery
- **Flexibility**: Multiple format support
- **Accessibility**: Semantic HTML and proper structure