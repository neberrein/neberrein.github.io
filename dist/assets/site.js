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

const syncGroups = new Map();
document.querySelectorAll('[data-sync-group]').forEach((video) => {
  const group = video.dataset.syncGroup;
  syncGroups.set(group, [...(syncGroups.get(group) || []), video]);
});

syncGroups.forEach((videos) => {
  const master = videos[0];
  const peers = videos.slice(1);
  let syncing = false;
  let sharedDuration = Infinity;
  let groupStarted = false;

  const runTogether = (action) => {
    if (syncing) return;
    syncing = true;
    videos.forEach(action);
    syncing = false;
  };

  const updateSharedDuration = () => {
    const durations = videos.map((video) => video.duration).filter(Number.isFinite);
    if (durations.length === videos.length) sharedDuration = Math.min(...durations);
  };

  const playGroup = (time = master.currentTime || 0) => {
    runTogether((video) => {
      if (Math.abs(video.currentTime - time) > 0.08) video.currentTime = time;
      video.muted = true;
      video.defaultMuted = true;
      video.play().catch(() => {});
    });
  };

  const tryAutoplayGroup = () => {
    if (groupStarted || videos.some((video) => video.readyState < 2)) return;
    groupStarted = true;
    playGroup(0);
  };

  videos.forEach((video) => {
    video.removeAttribute('loop');
    video.addEventListener('loadedmetadata', () => {
      updateSharedDuration();
      tryAutoplayGroup();
    });
    video.addEventListener('loadeddata', tryAutoplayGroup);
    video.addEventListener('canplay', tryAutoplayGroup);
    video.addEventListener('play', () => {
      if (!syncing) playGroup(video.currentTime);
    });
    video.addEventListener('seeking', () => runTogether((item) => {
      if (item !== video) item.currentTime = video.currentTime;
    }));
  });

  master.addEventListener('timeupdate', () => {
    if (Number.isFinite(sharedDuration) && master.currentTime >= sharedDuration - 0.08) {
      playGroup(0);
      return;
    }
    peers.forEach((peer) => {
      if (Math.abs(peer.currentTime - master.currentTime) > 0.08) peer.currentTime = master.currentTime;
    });
  });

  tryAutoplayGroup();
});

const autoplayVideos = [...document.querySelectorAll('video[autoplay]')];
const playMuted = (video) => {
  video.muted = true;
  video.defaultMuted = true;
  video.play().catch(() => {});
};

autoplayVideos.forEach((video) => {
  const start = Number(video.dataset.start || 0);
  if (start > 0) {
    video.addEventListener('loadedmetadata', () => {
      video.currentTime = Math.min(start, Math.max(0, video.duration - 0.05));
      playMuted(video);
    }, { once: true });
    video.addEventListener('timeupdate', () => {
      if (video.currentTime < start - 0.25) video.currentTime = Math.min(start, Math.max(0, video.duration - 0.05));
    });
  }
  if (video.readyState >= 2) playMuted(video);
  video.addEventListener('loadeddata', () => playMuted(video), { once: true });
  video.addEventListener('canplay', () => playMuted(video), { once: true });
});

if ('IntersectionObserver' in window) {
  const videoObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      const video = entry.target;
      if (entry.isIntersecting) playMuted(video);
    });
  }, { threshold: 0.25 });
  autoplayVideos.forEach((video) => videoObserver.observe(video));
}
