// Ant Design 主题配置
export const antdTheme = {
  token: {
    // 主色调 - 使用 AskDB 品牌色
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1890ff',
    
    // 圆角
    borderRadius: 6,
    
    // 字体
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontSize: 14,
    
    // 间距
    padding: 16,
    paddingXS: 8,
    paddingSM: 12,
    paddingLG: 24,
    paddingXL: 32,
  },
  
  components: {
    Layout: {
      bodyBg: '#f0f2f5',
      headerBg: '#001529',
      siderBg: '#001529',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#1890ff',
      itemSelectedColor: '#ffffff',
      itemHoverBg: 'rgba(24, 144, 255, 0.1)',
      itemColor: '#262626',
      itemHoverColor: '#1890ff',
    },
    Table: {
      headerBg: '#fafafa',
      headerColor: '#262626',
    },
    Card: {
      borderRadius: 8,
    },
    Button: {
      borderRadius: 6,
    },
    Input: {
      borderRadius: 6,
    },
  }
}


