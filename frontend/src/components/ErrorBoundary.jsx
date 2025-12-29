import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    this.setState({ error, info });
    console.error('ErrorBoundary caught error:', error, info);
    // Optionally: send to remote logging here
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <h2 className="text-lg font-semibold text-red-600">An error occurred rendering this view</h2>
          <div className="mt-3 text-sm text-gray-700">
            <div><strong>Error:</strong> {String(this.state.error?.message || this.state.error)}</div>
            {this.state.info?.componentStack && (
              <pre className="mt-2 text-xs text-gray-600 whitespace-pre-wrap">{this.state.info.componentStack}</pre>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
