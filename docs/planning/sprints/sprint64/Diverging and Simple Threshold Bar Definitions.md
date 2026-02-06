# Reviewed Technical Specifications

The provided specifications for the Diverging Threshold Bar and Simple Diverging Bar contain several omissions, such as missing mathematical symbols (e.g., the threshold variable $\theta$), incomplete conditions in the logic gates, and placeholders for equations and variables. These gaps have been addressed based on standard conventions from similar visualizations and prior contextual definitions, ensuring completeness and accuracy. The addition of "or vertical" to both definitions has been incorporated, allowing flexibility in orientation (horizontal by default, with vertical as an option for space-constrained interfaces). The structures remain consistent with established patterns for clarity in implementation.

Below are the corrected and reviewed versions, formatted in structured markdown for reference during web front-end development.

## Technical Specification: Diverging Threshold Bar

### Definition

A Diverging Threshold Bar is a horizontal or vertical, composite data visualization component designed to represent the "Advance-Decline" sentiment within a dataset. It centers the population of a single category around a zero-point baseline and partitions individual data points into four discrete Intensity Zones based on a configurable sensitivity threshold ($\theta$).

### The Four Segments (Logic Gates)

For each category, data points must be classified into one of the following four segments. The default threshold is $\theta = 10\%$.

| Segment Name       | Visual Mapping | Mathematical Condition    | Behavioral Intent                  |
|--------------------|----------------|---------------------------|-----------------------------------|
| Significant Decline | Far Left (Dark) | $x < -\theta$            | Highlights extreme negative outliers. |
| Minor Decline      | Inner Left (Light) | $-\theta \le x < 0$      | Shows "soft" negative sentiment.  |
| Minor Advance      | Inner Right (Light) | $0 \le x < \theta$       | Shows "soft" positive sentiment.  |
| Significant Advance | Far Right (Dark) | $x \ge \theta$           | Highlights extreme positive outliers. |

### Instructive Implementation Logic

To generate this bar programmatically, implement the following three sequential steps in Python functions:

1. **Population Binning**  
   Iterate through the raw values ($x_1, x_2, \dots, x_n$) for the category. Assign each value to one of the four bins according to the Logic Gates defined above.  
   *Note*: The threshold $\theta$ should be implemented as a variable parameter, defaulting to 0.10.

2. **Relative Frequency Calculation**  
   Compute the percentage of the total population ($N$) represented by each bin:  
   $$P_{segment} = \frac{Count_{segment}}{N} \times 100$$  
   The sum of the four percentages must equal 100%.

3. **Coordinate Mapping (The "Divergence")**  
   Map the percentages to a coordinate system with the baseline at $x=0$:  
   - Negative Offset: Render "Significant Decline" and "Minor Decline" as negative widths (e.g., a 30% decline extends from 0 to -30).  
   - Positive Offset: Render "Minor Advance" and "Significant Advance" as positive widths (e.g., a 40% advance extends from 0 to +40).

### Visual Objective

The rendered bar delivers two key insights:  
1. **Total Magnitude**: The overall horizontal width encapsulates the full 100% population.  
2. **Sentiment Shift**: The distribution of weight (left versus right of the baseline) reveals the net directional momentum of the category.

## Technical Specification: Simple Diverging Bar

### Definition

A Simple Diverging Bar is a horizontal or vertical, composite data visualization component designed to represent the "Advance-Decline" sentiment within a dataset. It centers the population of a single category around a zero-point baseline and partitions individual data points into two discrete segments based solely on directionality relative to zero, without additional intensity thresholds.

### The Two Segments (Logic Gates)

For each category, data points must be classified into one of the following two segments.

| Segment Name | Visual Mapping | Mathematical Condition | Behavioral Intent               |
|--------------|----------------|------------------------|---------------------------------|
| Decline     | Left (Red tones) | $x < 0$              | Highlights negative sentiment. |
| Advance     | Right (Green tones) | $x \ge 0$           | Highlights positive sentiment. |

### Instructive Implementation Logic

To generate this bar programmatically, implement the following three sequential steps in Python functions:

1. **Population Binning**  
   Iterate through the raw values ($x_1, x_2, \dots, x_n$) for the category. Assign each value to one of the two bins according to the Logic Gates defined above.

2. **Relative Frequency Calculation**  
   Compute the percentage of the total population ($N$) represented by each bin:  
   $$P_{segment} = \frac{Count_{segment}}{N} \times 100$$  
   The sum of the two percentages must equal 100%.

3. **Coordinate Mapping (The "Divergence")**  
   Map the percentages to a coordinate system with the baseline at $x=0$:  
   - Negative Offset: Render "Decline" as a negative width (e.g., a 40% decline extends from 0 to -40).  
   - Positive Offset: Render "Advance" as a positive width (e.g., a 60% advance extends from 0 to +60).

### Visual Objective

The rendered bar delivers two key insights:  
1. **Total Magnitude**: The overall horizontal width encapsulates the full 100% population.  
2. **Sentiment Shift**: The distribution of weight (left versus right of the baseline) reveals the net directional momentum of the category.

