---
title: "Diagrams and Flowcharts"
date: 2019-03-06
description: "Guide to Mermaid usage in Congo"
summary: "It's easy to add diagrams and flowcharts to articles using Mermaid."
tags: ["mermaid", "sample", "diagram", "shortcodes"]
---

# Diagrams

Mermaid diagrams are supported in Congo using the `mermaid` shortcode. Simply wrap the diagram markup within the shortcode. Congo automatically themes Mermaid diagrams to match the configured `colorScheme` parameter.

Refer to the [mermaid shortcode](https://jpanther.github.io/congo/docs/shortcodes/#mermaid) docs for more details.

The examples below are a small selection taken from the [official Mermaid docs](https://mermaid-js.github.io/mermaid/). You can also [view the page source](https://raw.githubusercontent.com/jpanther/congo/dev/exampleSite/content/samples/diagrams-flowcharts/index.md) on GitHub to see the markup.

## Flowchart

{{< mermaid >}}
graph TD
A[Christmas] -->|Get money| B(Go shopping)
B --> C{Let me think}
B --> G[/Another/]
C ==>|One| D[Laptop]
C -->|Two| E[iPhone]
C -->|Three| F[Car]
subgraph Section
C
D
E
F
G
end
{{< /mermaid >}}

## Sequence diagram

{{< mermaid >}}
sequenceDiagram
autonumber
par Action 1
Alice->>John: Hello John, how are you?
and Action 2
Alice->>Bob: Hello Bob, how are you?
end
Alice->>+John: Hello John, how are you?
Alice->>+John: John, can you hear me?
John-->>-Alice: Hi Alice, I can hear you!
Note right of John: John is perceptive
John-->>-Alice: I feel great!
loop Every minute
John-->Alice: Great!
end
{{< /mermaid >}}

## Class diagram

{{< mermaid >}}
classDiagram
Animal "1" <|-- Duck
Animal <|-- Fish
Animal <--o Zebra
Animal : +int age
Animal : +String gender
Animal: +isMammal()
Animal: +mate()
class Duck{
+String beakColor
+swim()
+quack()
}
class Fish{
-int sizeInFeet
-canEat()
}
class Zebra{
+bool is_wild
+run()
}
{{< /mermaid >}}

## Entity relationship diagram

{{< mermaid >}}
erDiagram
CUSTOMER }|..|{ DELIVERY-ADDRESS : has
CUSTOMER ||--o{ ORDER : places
CUSTOMER ||--o{ INVOICE : "liable for"
DELIVERY-ADDRESS ||--o{ ORDER : receives
INVOICE ||--|{ ORDER : covers
ORDER ||--|{ ORDER-ITEM : includes
PRODUCT-CATEGORY ||--|{ PRODUCT : contains
PRODUCT ||--o{ ORDER-ITEM : "ordered in"
{{< /mermaid >}}

# Chart

Congo includes support for Chart.js using the `chart` shortcode. Simply wrap the chart markup within the shortcode. Congo automatically themes charts to match the configured `colorScheme` parameter, however the colours can be customised using normal Chart.js syntax.

Refer to the [chart shortcode](https://jpanther.github.io/congo/docs/shortcodes/#chart) docs for more details.

The examples below are a small selection taken from the [official Chart.js docs](https://www.chartjs.org/docs/latest/samples). You can also [view the page source](https://raw.githubusercontent.com/jpanther/congo/dev/exampleSite/content/samples/charts/index.md) on GitHub to see the markup.

## Bar chart

<!-- prettier-ignore-start -->
{{< chart >}}
type: 'bar',
data: {
  labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
  datasets: [{
    label: 'My First Dataset',
    data: [65, 59, 80, 81, 56, 55, 40],
    backgroundColor: [
      'rgba(255, 99, 132, 0.2)',
      'rgba(255, 159, 64, 0.2)',
      'rgba(255, 205, 86, 0.2)',
      'rgba(75, 192, 192, 0.2)',
      'rgba(54, 162, 235, 0.2)',
      'rgba(153, 102, 255, 0.2)',
      'rgba(201, 203, 207, 0.2)'
    ],
    borderColor: [
      'rgb(255, 99, 132)',
      'rgb(255, 159, 64)',
      'rgb(255, 205, 86)',
      'rgb(75, 192, 192)',
      'rgb(54, 162, 235)',
      'rgb(153, 102, 255)',
      'rgb(201, 203, 207)'
    ],
    borderWidth: 1
  }]
}
{{< /chart >}}
<!-- prettier-ignore-end -->

## Line chart

<!-- prettier-ignore-start -->
{{< chart >}}
type: 'line',
data: {
  labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
  datasets: [{
    label: 'My First Dataset',
    data: [65, 59, 80, 81, 56, 55, 40],
    tension: 0.2
  }]
}
{{< /chart >}}
<!-- prettier-ignore-end -->

## Doughnut chart

<!-- prettier-ignore-start -->
{{< chart >}}
type: 'doughnut',
data: {
  labels: ['Red', 'Blue', 'Yellow'],
  datasets: [{
    label: 'My First Dataset',
    data: [300, 50, 100],
    backgroundColor: [
      'rgba(255, 99, 132, 0.7)',
      'rgba(54, 162, 235, 0.7)',
      'rgba(255, 205, 86, 0.7)'
    ],
    borderWidth: 0,
    hoverOffset: 4
  }]
}
{{< /chart >}}
<!-- prettier-ignore-end -->