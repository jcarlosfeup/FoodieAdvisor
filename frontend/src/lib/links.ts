/** Opens turn-by-turn directions in the user's maps app (a plain link; no map data is fetched). */
export function directionsUrl(latitude: number, longitude: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}`;
}

/** OSM websites are free text; only http(s) links are rendered. */
export function safeWebsite(url: string | null): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.toString() : null;
  } catch {
    return null;
  }
}

export function phoneHref(phone: string | null): string | null {
  if (!phone) return null;
  // OSM phone tags may hold several numbers separated by ";". Link the first one.
  const first = phone.split(";")[0]?.replace(/[^\d+]/g, "") ?? "";
  return first ? `tel:${first}` : null;
}
