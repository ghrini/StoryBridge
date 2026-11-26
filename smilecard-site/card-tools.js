// Helpers shared by the Card Gallery and Jacob's Heart pages.
const MEDIA = 'https://static.wixstatic.com/media/';
const FAVOURITES_KEY = 'smilecard-favourites';

// Square preview, cropped by Wix's image service.
export const thumb = (id, size = 400) => `${MEDIA}${id}/v1/fill/w_${size},h_${size},q_85/i.${id.split('.').pop()}`;

// The full-size card.
export const full = id => MEDIA + id;

// Same file, but Wix sends it as a download (dn = the file name it is saved under).
export const download = id => `${MEDIA}${id}?dn=SmileCard-card-${id.slice(7, 15)}.${id.split('.').pop()}`;

// Favourites live only in this browser (no account needed). Storage can be blocked, so never fail on it.
export function loadFavourites() {
  try {
    const saved = JSON.parse(localStorage.getItem(FAVOURITES_KEY) || '[]');
    return new Set(Array.isArray(saved) ? saved.filter(x => typeof x === 'string') : []);
  } catch {
    return new Set();
  }
}

export function saveFavourites(favourites) {
  try {
    localStorage.setItem(FAVOURITES_KEY, JSON.stringify([...favourites]));
  } catch {
    // private window or storage turned off: favourites last until the page is closed
  }
}

export function toggled(favourites, id) {
  const next = new Set(favourites);
  if (next.has(id)) next.delete(id); else next.add(id);
  saveFavourites(next);
  return next;
}
