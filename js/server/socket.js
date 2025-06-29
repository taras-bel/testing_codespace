module.exports = (io, socket) => {
  console.log('Socket connected:', socket.id);

  socket.on('editor:change', (data) => {
    socket.broadcast.emit('editor:update', data);
  });

  socket.on('disconnect', () => {
    console.log('Socket disconnected:', socket.id);
  });
};