import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-2xl font-semibold tracking-tight">Página no encontrada</h1>
      <p className="text-muted-foreground">La dirección que abriste no existe en AquaMetric.</p>
      <Link
        to="/"
        className="w-fit rounded-md text-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none"
      >
        Volver al inicio
      </Link>
    </section>
  );
}
