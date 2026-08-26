import React from 'react';

/* Last-resort guard: an unexpected render exception must not blank the
   whole app. Uses the existing card/alert styles — no new visual language. */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('Unhandled UI error:', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="app">
          <div className="alert alert-error" role="alert">
            <h3>Something went wrong</h3>
            <p>An unexpected error occurred while rendering the page.</p>
            <p className="small">
              <button className="btn btn-outline btn-sm" onClick={() => window.location.reload()}>
                Reload
              </button>
            </p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
