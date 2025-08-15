#!/usr/bin/env python3
"""
Trace Visualization Generator
Creates interactive HTML reports from trace analysis.
Part of the test_*trace*.py suite.
"""
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def generate_html_report(filename='trace_all.json', trace_path='./logs/trace/', output_path=None):
    """
    Generate interactive HTML visualization of trace data.
    
    Args:
        filename: Full filename including .json extension
        trace_path: Path to trace directory
        output_path: Optional output path for HTML file
    """
    # Construct full path
    full_path = os.path.join(trace_path, filename)
    
    if not os.path.exists(full_path):
        print(f"Error: File not found: {full_path}")
        sys.exit(1)
    
    with open(full_path, 'r') as f:
        data = json.load(f)
    
    print(f"Analyzing: {full_path}")
    
    # Extract basic info
    ticker = data.get('ticker', 'UNKNOWN')
    duration = data.get('duration_seconds', 0)
    steps = data.get('steps', [])
    
    # Generate summary from steps if not present
    if 'summary' not in data:
        summary = generate_summary_from_steps(steps)
    else:
        summary = data.get('summary', {})
    
    # Prepare chart data
    chart_data = prepare_chart_data(summary, steps)
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trace Analysis - {ticker}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <style>
        {generate_css()}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Trace Analysis Report</h1>
            <div class="info">
                <h2>{ticker}</h2>
                <p>Duration: {duration:.1f}s | Steps: {len(steps):,}</p>
            </div>
        </div>
        
        {generate_summary_cards(summary)}
        
        <div class="section">
            <h2>Event Flow Pipeline</h2>
            <div class="chart-container">
                <canvas id="flowChart"></canvas>
            </div>
        </div>
        
        <div class="section">
            <h2>Component Performance</h2>
            <div class="chart-grid">
                <div class="chart-item">
                    <canvas id="componentChart"></canvas>
                </div>
                <div class="chart-item">
                    <canvas id="efficiencyChart"></canvas>
                </div>
            </div>
        </div>
        
        {generate_event_details(summary)}
        
        <div class="footer">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
    
    <script>
        const chartData = {json.dumps(chart_data, indent=2)};
        {generate_javascript()}
    </script>
</body>
</html>"""
    
    # Save HTML
    if output_path is None:
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(trace_path, 'analysis', f"{base_name}_report.html")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML report generated: {output_path}")
    return output_path

def generate_summary_from_steps(steps: List[Dict]) -> Dict:
    """Generate summary data from trace steps"""
    # Initialize counters
    events_generated = defaultdict(int)
    events_emitted = defaultdict(int)
    component_timings = defaultdict(float)
    user_connections = {
        'first_user_time': None,
        'events_before_first_user': 0,
        'total_users': 0,
        'raw_efficiency': 0,
        'adjusted_efficiency': 0
    }
    
    # Process traces
    first_user_time = None
    events_before_user = 0
    
    for trace in steps:
        action = trace.get('action', '')
        component = trace.get('component', '')
        timestamp = trace.get('timestamp', 0)
        data = trace.get('data', {})
        
        # Handle string data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = {}
        
        details = data.get('details', {})
        duration = trace.get('duration_to_next_ms', 0)
        
        # Track component timings
        if duration > 0:
            component_timings[component] += duration / 1000.0
        
        # Track user connections
        if action == 'user_connected' and component == 'WebSocketManager' and first_user_time is None:
            first_user_time = timestamp
            user_connections['first_user_time'] = first_user_time
            user_connections['total_users'] = 1
        
        # Count events
        if action == 'event_detected':
            event_type = details.get('event_type', '')
            if event_type and event_type != 'unknown':
                # Normalize event type to plural
                if not event_type.endswith('s'):
                    event_type = event_type + 's'
                events_generated[event_type] += 1
                
                if first_user_time is None or timestamp < first_user_time:
                    events_before_user += 1
        
        elif action == 'event_emitted':
            event_type = details.get('event_type', '')
            if event_type and event_type != 'unknown':
                # Normalize event type to plural
                if not event_type.endswith('s'):
                    event_type = event_type + 's'
                events_emitted[event_type] += 1
    
    # Calculate efficiencies
    total_gen = sum(events_generated.values())
    total_emit = sum(events_emitted.values())
    
    user_connections['events_before_first_user'] = events_before_user
    if total_gen > 0:
        user_connections['raw_efficiency'] = (total_emit / total_gen) * 100
        adjusted_gen = total_gen - events_before_user
        if adjusted_gen > 0:
            user_connections['adjusted_efficiency'] = (total_emit / adjusted_gen) * 100
    
    return {
        'events_generated': dict(events_generated),
        'events_emitted': dict(events_emitted),
        'component_timings': dict(component_timings),
        'user_connections': user_connections,
        'counters': {
            'events_detected_total': total_gen,
            'events_emitted_total': total_emit,
            'events_before_first_user': events_before_user
        }
    }

def prepare_chart_data(summary: Dict, steps: List[Dict]) -> Dict:
    """Prepare data for Chart.js visualizations."""
    # Event flow data
    events_gen = summary.get('events_generated', {})
    events_emit = summary.get('events_emitted', {})
    
    flow_labels = ['Generated', 'Emitted']
    flow_datasets = []
    
    for event_type in ['highs', 'lows', 'surges', 'trends']:
        gen = events_gen.get(event_type, 0)
        emit = events_emit.get(event_type, 0)
        
        if gen > 0 or emit > 0:
            dataset = {
                'label': event_type.capitalize(),
                'data': [gen, emit],
                'backgroundColor': get_color_for_type(event_type, 0.5),
                'borderColor': get_color_for_type(event_type, 1),
                'borderWidth': 1
            }
            flow_datasets.append(dataset)
    
    # Component timing data
    component_timings = summary.get('component_timings', {})
    sorted_components = sorted(component_timings.items(), key=lambda x: x[1], reverse=True)[:10]
    
    component_labels = [comp[0] for comp in sorted_components]
    component_values = [comp[1] for comp in sorted_components]
    
    # Efficiency data
    efficiency_labels = []
    efficiency_values = []
    
    for event_type in ['highs', 'lows', 'surges', 'trends']:
        gen = events_gen.get(event_type, 0)
        emit = events_emit.get(event_type, 0)
        if gen > 0:
            efficiency_labels.append(event_type.capitalize())
            efficiency_values.append((emit / gen) * 100)
    
    return {
        'flow': {
            'labels': flow_labels,
            'datasets': flow_datasets
        },
        'components': {
            'labels': component_labels,
            'values': component_values
        },
        'efficiency': {
            'labels': efficiency_labels,
            'values': efficiency_values
        }
    }

def get_color_for_type(event_type: str, alpha: float) -> str:
    """Get color for event type."""
    colors = {
        'highs': f'rgba(59, 130, 246, {alpha})',    # Blue
        'lows': f'rgba(239, 68, 68, {alpha})',      # Red
        'surges': f'rgba(245, 158, 11, {alpha})',   # Yellow
        'trends': f'rgba(139, 92, 246, {alpha})'    # Purple
    }
    return colors.get(event_type, f'rgba(107, 114, 128, {alpha})')

def generate_summary_cards(summary: Dict) -> str:
    """Generate summary cards HTML."""
    user_connections = summary.get('user_connections', {})
    counters = summary.get('counters', {})
    
    cards = [
        {
            'title': 'Raw Efficiency',
            'value': f"{user_connections.get('raw_efficiency', 0):.1f}%",
            'subtitle': 'All events'
        },
        {
            'title': 'Adjusted Efficiency',
            'value': f"{user_connections.get('adjusted_efficiency', 0):.1f}%",
            'subtitle': 'After user connection'
        },
        {
            'title': 'Events Before User',
            'value': str(user_connections.get('events_before_first_user', counters.get('events_before_first_user', 0))),
            'subtitle': 'Lost events'
        },
        {
            'title': 'Total Events',
            'value': str(counters.get('events_detected_total', 0)),
            'subtitle': 'Detected'
        }
    ]
    
    html = '<div class="summary-grid">'
    for card in cards:
        html += f"""
        <div class="summary-card">
            <div class="metric-title">{card['title']}</div>
            <div class="metric-value">{card['value']}</div>
            <div class="metric-subtitle">{card['subtitle']}</div>
        </div>
        """
    html += '</div>'
    
    return html

def generate_event_details(summary: Dict) -> str:
    """Generate event details section."""
    events_gen = summary.get('events_generated', {})
    events_emit = summary.get('events_emitted', {})
    
    html = '<div class="section"><h2>Event Details</h2>'
    
    for event_type in ['highs', 'lows', 'surges', 'trends']:
        gen = events_gen.get(event_type, 0)
        emit = events_emit.get(event_type, 0)
        
        if gen > 0 or emit > 0:
            efficiency = (emit / gen * 100) if gen > 0 else 0
            status = "✅" if efficiency == 100 else "⚠️" if efficiency > 80 else "❌"
            
            html += f"""
            <div class="event-detail">
                <h3>{status} {event_type.capitalize()}</h3>
                <div class="flow-stages">
                    <span class="stage">{gen}</span> generated → 
                    <span class="stage">{emit}</span> emitted
                    <span class="efficiency">({efficiency:.1f}% efficiency)</span>
                </div>
            </div>
            """
    
    html += '</div>'
    return html

def generate_css() -> str:
    """Generate CSS styles."""
    return """
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background-color: #f3f4f6;
        margin: 0;
        padding: 0;
        color: #1f2937;
    }
    
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }
    
    .header {
        background: white;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    h1 {
        margin: 0 0 10px 0;
        color: #1f2937;
    }
    
    h2 {
        margin: 0;
        color: #4b5563;
    }
    
    .section {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    .chart-container {
        position: relative;
        height: 400px;
        margin: 20px 0;
    }
    
    .chart-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
    }
    
    .chart-item {
        position: relative;
        height: 300px;
    }
    
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin: 20px 0;
    }
    
    .summary-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .metric-title {
        color: #6b7280;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f2937;
        margin: 10px 0;
    }
    
    .metric-subtitle {
        color: #9ca3af;
        font-size: 0.875rem;
    }
    
    .event-detail {
        padding: 15px;
        border-left: 4px solid #3b82f6;
        margin: 15px 0;
        background: #f9fafb;
    }
    
    .flow-stages {
        margin-top: 10px;
        font-size: 1.1rem;
    }
    
    .stage {
        font-weight: bold;
        color: #3b82f6;
    }
    
    .efficiency {
        color: #6b7280;
        margin-left: 10px;
    }
    
    .footer {
        text-align: center;
        color: #9ca3af;
        padding: 20px;
        font-size: 0.875rem;
    }
    
    @media (max-width: 768px) {
        .chart-grid {
            grid-template-columns: 1fr;
        }
    }
    """

def generate_javascript() -> str:
    """Generate JavaScript for charts."""
    return """
    // Event Flow Chart
    const flowCtx = document.getElementById('flowChart');
    if (flowCtx && chartData.flow.datasets.length > 0) {
        new Chart(flowCtx, {
            type: 'bar',
            data: chartData.flow,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Event Flow Pipeline'
                    },
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        stacked: false
                    },
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // Component Performance Chart
    const componentCtx = document.getElementById('componentChart');
    if (componentCtx && chartData.components.labels.length > 0) {
        new Chart(componentCtx, {
            type: 'doughnut',
            data: {
                labels: chartData.components.labels,
                datasets: [{
                    data: chartData.components.values,
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.7)',
                        'rgba(239, 68, 68, 0.7)',
                        'rgba(245, 158, 11, 0.7)',
                        'rgba(16, 185, 129, 0.7)',
                        'rgba(139, 92, 246, 0.7)',
                        'rgba(107, 114, 128, 0.7)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Time by Component'
                    },
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
    
    // Efficiency Chart
    const efficiencyCtx = document.getElementById('efficiencyChart');
    if (efficiencyCtx && chartData.efficiency.labels.length > 0) {
        new Chart(efficiencyCtx, {
            type: 'bar',
            data: {
                labels: chartData.efficiency.labels,
                datasets: [{
                    label: 'Efficiency %',
                    data: chartData.efficiency.values,
                    backgroundColor: chartData.efficiency.values.map(v => 
                        v >= 90 ? 'rgba(16, 185, 129, 0.7)' :
                        v >= 70 ? 'rgba(245, 158, 11, 0.7)' :
                        'rgba(239, 68, 68, 0.7)'
                    )
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Event Type Efficiency'
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
    """

def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate HTML visualization report from trace data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                           # Use default trace_all.json
  %(prog)s NVDA.json                 # Generate report for specific file
  %(prog)s NVDA.json /path/ out.html # Custom paths
        '''
    )
    
    parser.add_argument('filename', nargs='?', default='trace_all.json',
                       help='Trace filename with .json extension (default: trace_all.json)')
    parser.add_argument('trace_path', nargs='?', default='./logs/trace/',
                       help='Path to trace directory (default: ./logs/trace/)')
    parser.add_argument('output', nargs='?', default=None,
                       help='Output HTML file path (optional)')
    
    args = parser.parse_args()
    
    generate_html_report(args.filename, args.trace_path, args.output)

if __name__ == "__main__":
    main()