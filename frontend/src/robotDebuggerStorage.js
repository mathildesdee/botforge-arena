// Shared localStorage keys bridging the Lobby (which knows the
// player's name, server-assigned id, and uploaded robot JSON) to the
// Arena (which needs all three to power the robot debugger — see
// robotDebugger.js for why this only ever works for your own robot).
export const MY_PLAYER_ID_KEY = 'botforge:my-player-id';
export const MY_ROBOT_KEY = 'botforge:my-robot';
