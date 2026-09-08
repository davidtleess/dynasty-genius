import { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { parsePlayerSearch, stringifyPlayerSearch } from "./lib/dg/search";
import { routeTree } from "./routeTree.gen";

export const getRouter = () => {
  const queryClient = new QueryClient();

  const router = createRouter({
    routeTree,
    parseSearch: parsePlayerSearch,
    stringifySearch: stringifyPlayerSearch,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
  });

  return router;
};
