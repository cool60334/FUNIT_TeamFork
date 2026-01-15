# JSON-LD Structured Data Templates (Google Standard)

These templates are based on the latest Google Search Central documentation (2026). Use these structures to generate valid JSON-LD for the `schema` field in Frontmatter.

> [!IMPORTANT]
> When combining multiple schema types (e.g., Article + FAQPage), you **MUST** use the `@graph` property. A top-level JSON array `[...]` is **INVALID** and will fail Google Rich Results Test.

## Multi-Type Schema Template (Required Format)

```json
{
  "@context": "https://schema.org",
  "@graph": [
    { "@type": "Article", ... },
    { "@type": "FAQPage", ... }
  ]
}
```

---
Use this for travel guides, news, and blog posts.

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{{TITLE}}",
  "description": "{{DESCRIPTION}}",
  "image": [
    "{{IMAGE_URL_16x9}}",
    "{{IMAGE_URL_4x3}}",
    "{{IMAGE_URL_1x1}}"
  ],
  "datePublished": "{{CURRENT_DATE}}T00:00:00+08:00",
  "dateModified": "{{CURRENT_DATE}}T00:00:00+08:00",
  "author": [{
    "@type": "Organization",
    "name": "FUNIT",
    "url": "https://test-funit.welcometw.com/"
  }],
  "publisher": {
    "@type": "Organization",
    "name": "FUNIT",
    "logo": {
      "@type": "ImageObject",
      "url": "https://test-funit.welcometw.com/wp-content/uploads/logo.png"
    }
  }
}
```

## 2. FAQ (FAQPage)
Use this for articles with a dedicated "Common Questions" section.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "{{QUESTION_1}}",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "{{ANSWER_1}}"
      }
    },
    {
      "@type": "Question",
      "name": "{{QUESTION_2}}",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "{{ANSWER_2}}"
      }
    }
  ]
}
```

## 3. Local Business (LocalBusiness / TravelAgency)
Use this for specific venue reviews or local service pages.

```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "{{BUSINESS_NAME}}",
  "image": "{{IMAGE_URL}}",
  "@id": "{{URL}}",
  "url": "{{URL}}",
  "telephone": "{{PHONE}}",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "{{STREET}}",
    "addressLocality": "{{CITY}}",
    "postalCode": "{{POSTAL_CODE}}",
    "addressCountry": "TW"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": {{LAT}},
    "longitude": {{LNG}}
  },
  "openingHoursSpecification": {
    "@type": "OpeningHoursSpecification",
    "dayOfWeek": [
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
      "Sunday"
    ],
    "opens": "09:00",
    "closes": "18:00"
  }
}
```

## 4. Organization (Organization)
Use this for the homepage or "About Us" page.

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "FUNIT",
  "url": "https://test-funit.welcometw.com/",
  "logo": "https://test-funit.welcometw.com/wp-content/uploads/logo.png",
  "sameAs": [
    "https://www.facebook.com/welcometw2020/",
    "https://www.instagram.com/funit_tw/",
    "https://www.youtube.com/@funit_tw"
  ]
}
```
