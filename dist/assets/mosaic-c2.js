(() => {
  const root = document.querySelector('[data-mosaic-recordings]');
  if (!root) return;
  const tabs = [...root.querySelectorAll('[role="tab"]')];
  const panels = [...root.querySelectorAll('[role="tabpanel"]')];
  function select(tab, focus = false) {
    tabs.forEach(item => {
      const active = item === tab;
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
    });
    panels.forEach(panel => {
      panel.hidden = panel.id !== tab.getAttribute('aria-controls');
      if (panel.hidden) panel.querySelector('video').pause();
    });
    if (focus) tab.focus();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => select(tab));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      select(tabs[next], true);
    });
  });
  panels.forEach(panel => {
    const video = panel.querySelector('video');
    panel.querySelectorAll('[data-seek]').forEach(button => {
      button.addEventListener('click', () => {
        video.pause();
        const seek = () => {
          video.currentTime = Math.min(Number(button.dataset.seek), Math.max(0, video.duration - .1));
          video.focus({ preventScroll: true });
        };
        if (video.readyState >= 1) seek();
        else {
          video.addEventListener('loadedmetadata', seek, { once: true });
          video.load();
        }
      });
    });
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) panels.forEach(panel => panel.querySelector('video').pause());
  });
})();
