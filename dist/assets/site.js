const navToggle = document.querySelector('[data-nav-toggle]');
const nav = document.querySelector('[data-nav]');

navToggle?.addEventListener('click', () => {
  const open = navToggle.getAttribute('aria-expanded') === 'true';
  navToggle.setAttribute('aria-expanded', String(!open));
  nav?.classList.toggle('is-open', !open);
});

nav?.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    nav.classList.remove('is-open');
    navToggle?.setAttribute('aria-expanded', 'false');
  });
});

document.querySelectorAll('[data-filter]').forEach((button) => {
  button.addEventListener('click', () => {
    const filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach((item) => {
      const active = item === button;
      item.classList.toggle('is-active', active);
      item.setAttribute('aria-pressed', String(active));
    });
    document.querySelectorAll('[data-category]').forEach((card) => {
      card.classList.toggle('is-hidden', filter !== 'all' && card.dataset.category !== filter);
    });
  });
});

const revealItems = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08 });
  revealItems.forEach((item) => observer.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add('is-visible'));
}

document.querySelectorAll('[data-sync-group]').forEach((video) => {
  const group = video.dataset.syncGroup;
  const peers = [...document.querySelectorAll(`[data-sync-group="${group}"]`)];
  let syncing = false;
  const withPeers = (action) => {
    if (syncing) return;
    syncing = true;
    peers.filter((peer) => peer !== video).forEach(action);
    syncing = false;
  };
  video.addEventListener('play', () => withPeers((peer) => {
    peer.currentTime = video.currentTime;
    peer.play().catch(() => {});
  }));
  video.addEventListener('pause', () => withPeers((peer) => peer.pause()));
  video.addEventListener('seeking', () => withPeers((peer) => { peer.currentTime = video.currentTime; }));
});
