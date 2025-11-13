#!/usr/bin/env python3
"""
TRX Viewer - Parse .trx test result files and generate reports
"""

import xml.etree.ElementTree as ET
import argparse
import sys
from datetime import datetime
from pathlib import Path


class TrxParser:
    """Parser for TRX (Visual Studio Test Results) files"""

    # TRX namespace
    NS = {'': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}

    def __init__(self, trx_file):
        self.trx_file = trx_file
        self.tree = None
        self.root = None
        self.results = []
        self.summary = {}

    def parse(self):
        """Parse the TRX file"""
        try:
            self.tree = ET.parse(self.trx_file)
            self.root = self.tree.getroot()
            self._parse_summary()
            self._parse_results()
            return True
        except Exception as e:
            print(f"Error parsing TRX file: {e}", file=sys.stderr)
            return False

    def _parse_summary(self):
        """Extract test run summary"""
        # Find ResultSummary element
        result_summary = self.root.find('.//ResultSummary', self.NS)
        counters = self.root.find('.//Counters', self.NS)

        if counters is not None:
            self.summary = {
                'total': int(counters.get('total', 0)),
                'executed': int(counters.get('executed', 0)),
                'passed': int(counters.get('passed', 0)),
                'failed': int(counters.get('failed', 0)),
                'error': int(counters.get('error', 0)),
                'timeout': int(counters.get('timeout', 0)),
                'aborted': int(counters.get('aborted', 0)),
                'inconclusive': int(counters.get('inconclusive', 0)),
                'not_executed': int(counters.get('notExecuted', 0)),
            }

        # Get test run info
        test_run = self.root
        if test_run is not None:
            self.summary['run_name'] = test_run.get('name', 'Unknown')
            self.summary['run_user'] = test_run.get('runUser', 'Unknown')

    def _parse_results(self):
        """Extract individual test results"""
        results_elem = self.root.find('.//Results', self.NS)

        if results_elem is not None:
            for unit_test_result in results_elem.findall('UnitTestResult', self.NS):
                result = {
                    'test_name': unit_test_result.get('testName', 'Unknown'),
                    'outcome': unit_test_result.get('outcome', 'Unknown'),
                    'duration': unit_test_result.get('duration', '0'),
                    'start_time': unit_test_result.get('startTime', ''),
                    'end_time': unit_test_result.get('endTime', ''),
                }

                # Get error message if test failed
                output_elem = unit_test_result.find('.//Output', self.NS)
                if output_elem is not None:
                    error_info = output_elem.find('.//ErrorInfo', self.NS)
                    if error_info is not None:
                        message = error_info.find('Message', self.NS)
                        stack_trace = error_info.find('StackTrace', self.NS)
                        result['error_message'] = message.text if message is not None else ''
                        result['stack_trace'] = stack_trace.text if stack_trace is not None else ''

                self.results.append(result)


class ReportGenerator:
    """Generate reports from parsed TRX data"""

    def __init__(self, parser):
        self.parser = parser

    def generate_console_report(self):
        """Generate a console-friendly report"""
        print("\n" + "="*80)
        print(f"TEST RESULTS REPORT")
        print("="*80)

        # Summary section
        summary = self.parser.summary
        print(f"\nTest Run: {summary.get('run_name', 'N/A')}")
        print(f"Run by: {summary.get('run_user', 'N/A')}")
        print("\n" + "-"*80)
        print("SUMMARY")
        print("-"*80)
        print(f"Total Tests:     {summary.get('total', 0)}")
        print(f"Executed:        {summary.get('executed', 0)}")
        print(f"Passed:          {summary.get('passed', 0)}")
        print(f"Failed:          {summary.get('failed', 0)}")
        print(f"Errors:          {summary.get('error', 0)}")
        print(f"Skipped:         {summary.get('not_executed', 0)}")
        print(f"Inconclusive:    {summary.get('inconclusive', 0)}")

        # Calculate pass rate
        total = summary.get('executed', 0)
        passed = summary.get('passed', 0)
        pass_rate = (passed / total * 100) if total > 0 else 0
        print(f"\nPass Rate:       {pass_rate:.2f}%")

        # Failed tests detail
        failed_tests = [r for r in self.parser.results if r['outcome'] == 'Failed']
        if failed_tests:
            print("\n" + "-"*80)
            print("FAILED TESTS")
            print("-"*80)
            for i, test in enumerate(failed_tests, 1):
                print(f"\n{i}. {test['test_name']}")
                print(f"   Duration: {test['duration']}")
                if 'error_message' in test:
                    print(f"   Error: {test['error_message'][:200]}")

        # Passed tests summary
        passed_tests = [r for r in self.parser.results if r['outcome'] == 'Passed']
        if passed_tests:
            print("\n" + "-"*80)
            print(f"PASSED TESTS ({len(passed_tests)})")
            print("-"*80)
            for test in passed_tests[:10]:  # Show first 10
                print(f"  ✓ {test['test_name']} ({test['duration']})")
            if len(passed_tests) > 10:
                print(f"  ... and {len(passed_tests) - 10} more")

        print("\n" + "="*80 + "\n")

    def generate_html_report(self, output_file):
        """Generate an HTML report"""
        summary = self.parser.summary
        total = summary.get('executed', 0)
        passed = summary.get('passed', 0)
        pass_rate = (passed / total * 100) if total > 0 else 0

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Results Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .summary-card {{
            background: #f9f9f9;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #4CAF50;
        }}
        .summary-card.failed {{
            border-left-color: #f44336;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
        }}
        .summary-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .pass-rate {{
            font-size: 48px;
            font-weight: bold;
            text-align: center;
            margin: 30px 0;
            color: {('#4CAF50' if pass_rate >= 80 else '#ff9800' if pass_rate >= 50 else '#f44336')};
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .passed {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .failed {{
            color: #f44336;
            font-weight: bold;
        }}
        .error-message {{
            color: #666;
            font-size: 0.9em;
            font-family: monospace;
            background: #f5f5f5;
            padding: 10px;
            margin-top: 5px;
            border-radius: 3px;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Test Results Report</h1>

        <div class="summary">
            <div class="summary-card">
                <h3>Total Tests</h3>
                <div class="value">{summary.get('total', 0)}</div>
            </div>
            <div class="summary-card">
                <h3>Passed</h3>
                <div class="value">{summary.get('passed', 0)}</div>
            </div>
            <div class="summary-card failed">
                <h3>Failed</h3>
                <div class="value">{summary.get('failed', 0)}</div>
            </div>
            <div class="summary-card">
                <h3>Skipped</h3>
                <div class="value">{summary.get('not_executed', 0)}</div>
            </div>
        </div>

        <div class="pass-rate">
            Pass Rate: {pass_rate:.1f}%
        </div>

        <h2>Test Details</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Outcome</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody>
"""

        for result in self.parser.results:
            outcome_class = 'passed' if result['outcome'] == 'Passed' else 'failed'
            html += f"""
                <tr>
                    <td>{result['test_name']}</td>
                    <td class="{outcome_class}">{result['outcome']}</td>
                    <td>{result['duration']}</td>
                </tr>
"""
            if 'error_message' in result and result['error_message']:
                html += f"""
                <tr>
                    <td colspan="3">
                        <div class="error-message">{result['error_message']}</div>
                    </td>
                </tr>
"""

        html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"HTML report generated: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Parse .trx test result files and generate reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s test-results.trx                    # Display console report
  %(prog)s test-results.trx --html report.html # Generate HTML report
  %(prog)s test-results.trx --html             # Generate HTML report (auto-named)
        """
    )

    parser.add_argument('trx_file', help='Path to the .trx file')
    parser.add_argument('--html', nargs='?', const='auto',
                        help='Generate HTML report (optionally specify output file)')

    args = parser.parse_args()

    # Check if file exists
    if not Path(args.trx_file).exists():
        print(f"Error: File not found: {args.trx_file}", file=sys.stderr)
        sys.exit(1)

    # Parse TRX file
    trx_parser = TrxParser(args.trx_file)
    if not trx_parser.parse():
        sys.exit(1)

    # Generate reports
    report_gen = ReportGenerator(trx_parser)

    if args.html:
        # Generate HTML report
        if args.html == 'auto':
            output_file = Path(args.trx_file).stem + '_report.html'
        else:
            output_file = args.html
        report_gen.generate_html_report(output_file)
    else:
        # Generate console report
        report_gen.generate_console_report()


if __name__ == '__main__':
    main()
