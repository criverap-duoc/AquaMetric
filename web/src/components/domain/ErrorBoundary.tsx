import { Component, type ErrorInfo, type ReactNode } from "react";

import { ErrorState } from "@/components/domain/ErrorState";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Turns a render crash into a retry banner instead of a blank page.
 *
 * React unmounts the whole tree when a render throws without a boundary — exactly how reading a
 * field of an unexpected payload turned two screens white. React only supports class components
 * for this (there is no hook), so no extra dependency is needed.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Kept in the console on purpose: the UI shows a human message, developers get the stack.
    console.error("[ui] render error", error, info.componentStack);
  }

  private readonly handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.error === null) {
      return this.props.children;
    }

    return (
      <ErrorState
        error={this.state.error}
        onRetry={this.handleReload}
        title="Esta pantalla falló al dibujarse."
        detail="Se produjo un error inesperado al dibujar la vista. Recarga la página para reintentar; el detalle técnico quedó en la consola del navegador."
        code="RENDER_ERROR"
      />
    );
  }
}
