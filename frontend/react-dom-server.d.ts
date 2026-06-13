declare module "react-dom/server" {
  import type { ReactElement, ReactNode } from "react";

  export function renderToStaticMarkup(element: ReactElement | ReactNode): string;
}
