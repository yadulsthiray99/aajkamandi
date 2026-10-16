// aajkamandi fetch relay (Cloudflare Worker).
// data.gov.in and NECC refuse connections from GitHub's (US) runners, but accept Cloudflare,
// so the daily GitHub job fetches through this relay. It is NOT an open proxy:
//  - only two upstreams are allowed (the Agmarknet dataset on api.data.gov.in, and the NECC egg sheet)
//  - every request must carry our data.gov.in key, checked against the DATA_GOV_API_KEY Worker secret
const DGOV_RESOURCES = new Set(["35985678-0d79-46b4-9ed6-6f13308a1d24"]);
const UA = "Mozilla/5.0 (compatible; aajkamandi-fetcher/1.0)";

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const parts = url.pathname.split("/").filter(Boolean);

    if (parts[0] === "dgov" && req.method === "GET") {
      if (!env.DATA_GOV_API_KEY || url.searchParams.get("api-key") !== env.DATA_GOV_API_KEY) return new Response("forbidden", { status: 403 });
      if (!DGOV_RESOURCES.has(parts[1])) return new Response("resource not allowed", { status: 400 });
      const up = await fetch(`https://api.data.gov.in/resource/${parts[1]}${url.search}`, { headers: { "User-Agent": UA } });
      return new Response(up.body, { status: up.status, headers: { "content-type": up.headers.get("content-type") || "application/json" } });
    }

    if (parts[0] === "necc" && req.method === "POST") {
      if (!env.DATA_GOV_API_KEY || req.headers.get("x-relay-key") !== env.DATA_GOV_API_KEY) return new Response("forbidden", { status: 403 });
      const up = await fetch("https://www.e2necc.com/home/eggprice", {
        method: "POST", body: await req.text(),
        headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded" },
      });
      return new Response(up.body, { status: up.status, headers: { "content-type": up.headers.get("content-type") || "text/html" } });
    }

    return new Response("not found", { status: 404 });
  },
};
