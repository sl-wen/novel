// 增加测试超时时间
jest.setTimeout(60000);
 
// 添加全局错误处理
process.on('unhandledRejection', (reason, promise) => {
  console.error('未处理的 Promise 拒绝:', promise, '原因:', reason);
}); 