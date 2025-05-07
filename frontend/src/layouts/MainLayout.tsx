// Admin menü kısmına eklenecek

<NavLink
  to="/admin/fine-tuning"
  className={({ isActive }) =>
    `flex items-center px-4 py-3 text-gray-700 dark:text-gray-300 rounded-md transition-colors ${
      isActive
        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
        : 'hover:bg-gray-100 dark:hover:bg-gray-700'
    }`
  }
  onClick={closeSidebar}
>
  <FaBrain className="mr-3" />
  <span>{t('admin.fineTuning')}</span>
</NavLink>