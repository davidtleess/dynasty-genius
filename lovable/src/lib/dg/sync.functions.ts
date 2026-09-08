import { createServerFn } from "@tanstack/react-start";
/** Never execute the imported prototype scorer or write to live Supabase. */
export const refreshEverything = createServerFn({ method: "POST" }).handler(async () => {
  throw new Error(
    "This interface reads the accepted DG snapshot. Refresh belongs to the DG backend.",
  );
});
