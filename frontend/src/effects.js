// Purely visual feedback — deliberately separate from game logic per
// docs/ARCHITECTURE.md's non-negotiable rule that simulation and
// rendering stay apart. Every function here just draws something
// transient and cleans itself up; none of them read authoritative
// state or decide anything about the match.

export function muzzleFlash(scene, x, y, direction) {
  const rad = Phaser.Math.DegToRad(direction);
  const flash = scene.add.circle(x + Math.cos(rad) * 20, y + Math.sin(rad) * 20, 6, 0xfff59d);
  scene.tweens.add({
    targets: flash,
    alpha: 0,
    scale: 1.8,
    duration: 120,
    onComplete: () => flash.destroy(),
  });
}

export function hitSpark(scene, x, y) {
  for (let i = 0; i < 6; i++) {
    const angle = Math.random() * Math.PI * 2;
    const dist = 12 + Math.random() * 10;
    const spark = scene.add.circle(x, y, 2, 0xffca28);
    scene.tweens.add({
      targets: spark,
      x: x + Math.cos(angle) * dist,
      y: y + Math.sin(angle) * dist,
      alpha: 0,
      duration: 250,
      onComplete: () => spark.destroy(),
    });
  }
  scene.cameras.main.shake(80, 0.002);
}

export function explosion(scene, x, y) {
  const ring = scene.add.circle(x, y, 6, 0xff7043, 0.5).setStrokeStyle(3, 0xff3d00);
  scene.tweens.add({
    targets: ring,
    scale: 6,
    alpha: 0,
    duration: 450,
    onComplete: () => ring.destroy(),
  });

  for (let i = 0; i < 10; i++) {
    const angle = Math.random() * Math.PI * 2;
    const dist = 20 + Math.random() * 30;
    const debris = scene.add.circle(x, y, 3, 0xffab40);
    scene.tweens.add({
      targets: debris,
      x: x + Math.cos(angle) * dist,
      y: y + Math.sin(angle) * dist,
      alpha: 0,
      duration: 500 + Math.random() * 200,
      onComplete: () => debris.destroy(),
    });
  }

  scene.cameras.main.shake(220, 0.006);
}

export function showBanner(scene, text, { holdMs = 1200, color = '#e8edf2' } = {}) {
  const label = scene.add
    .text(400, 260, text, { fontSize: '36px', color, fontStyle: 'bold' })
    .setOrigin(0.5)
    .setAlpha(0)
    .setDepth(20);
  scene.tweens.add({
    targets: label,
    alpha: 1,
    duration: 200,
    yoyo: true,
    hold: holdMs,
    onComplete: () => label.destroy(),
  });
}

export function showCountdown(scene, steps = ['3', '2', '1', 'FIGHT!'], stepMs = 700) {
  steps.forEach((step, i) => {
    scene.time.delayedCall(i * stepMs, () => {
      showBanner(scene, step, { holdMs: stepMs - 250 });
    });
  });
}
