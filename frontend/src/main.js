import ArenaScene from './scenes/ArenaScene.js';

const config = {
  type: Phaser.AUTO,
  width: 800,
  height: 600,
  parent: 'arena',
  backgroundColor: '#0b0e13',
  scene: [ArenaScene],
};

new Phaser.Game(config);
