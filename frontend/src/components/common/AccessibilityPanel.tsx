import React, { useState } from 'react';
import { FiType, FiEye, FiZap, FiSettings, FiVolume2, FiX, FiMonitor } from 'react-icons/fi';
import { motion, AnimatePresence } from 'framer-motion';
import { useAccessibility } from './AccessibilityProvider';
import Button from './Button';

const AccessibilityPanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { settings, updateSettings, resetSettings } = useAccessibility();

  const togglePanel = () => {
    setIsOpen(!isOpen);
  };

  // Animasyon varyasyonları
  const panelVariants = {
    closed: {
      opacity: 0,
      x: '100%',
      transition: {
        duration: settings.reduceMotion ? 0.1 : 0.3,
      }
    },
    open: {
      opacity: 1,
      x: 0,
      transition: {
        duration: settings.reduceMotion ? 0.1 : 0.3,
      }
    }
  };

  return (
    <>
      {/* Erişilebilirlik butonu - sabit konumlu */}
      <button
        className="fixed right-4 bottom-4 p-3 bg-blue-600 text-white rounded-full shadow-lg z-30 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        onClick={togglePanel}
        aria-label="Erişilebilirlik ayarları"
        aria-expanded={isOpen}
      >
        <FiSettings size={24} />
      </button>

      {/* Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial="closed"
            animate="open"
            exit="closed"
            variants={panelVariants}
            className="fixed right-0 top-0 h-full w-80 max-w-full bg-white dark:bg-gray-800 shadow-lg z-40 overflow-y-auto"
            role="dialog"
            aria-modal="true"
            aria-labelledby="accessibility-title"
          >
            <div className="p-4">
              <div className="flex justify-between items-center mb-4">
                <h2 id="accessibility-title" className="text-xl font-medium text-gray-900 dark:text-white">
                  Erişilebilirlik Ayarları
                </h2>
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  aria-label="Kapat"
                >
                  <FiX size={24} />
                </button>
              </div>

              <div className="space-y-6">
                {/* Metin Boyutu */}
                <div>
                  <h3 className="flex items-center text-lg font-medium text-gray-900 dark:text-white mb-2">
                    <FiType className="mr-2" />
                    Metin Boyutu
                  </h3>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => updateSettings({ textSize: Math.max(0.8, settings.textSize - 0.1) })}
                      className="p-2 bg-gray-200 dark:bg-gray-700 rounded-md text-gray-800 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600"
                      aria-label="Metni küçült"
                    >
                      A-
                    </button>
                    <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500"
                        style={{ width: `${((settings.textSize - 0.8) / 0.6) * 100}%` }}
                      ></div>
                    </div>
                    <button
                      onClick={() => updateSettings({ textSize: Math.min(1.4, settings.textSize + 0.1) })}
                      className="p-2 bg-gray-200 dark:bg-gray-700 rounded-md text-gray-800 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600"
                      aria-label="Metni büyüt"
                    >
                      A+
                    </button>
                  </div>
                </div>

                {/* Yüksek Kontrast */}
                <div>
                  <h3 className="flex items-center text-lg font-medium text-gray-900 dark:text-white mb-2">
                    <FiEye className="mr-2" />
                    Görünüm
                  </h3>
                  <div className="flex flex-col space-y-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={settings.highContrast}
                        onChange={(e) => updateSettings({ highContrast: e.target.checked })}
                        className="form-checkbox h-5 w-5 text-blue-600"
                      />
                      <span className="ml-2 text-gray-700 dark:text-gray-300">Yüksek Kontrast</span>
                    </label>
                    
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={settings.focusVisible}
                        onChange={(e) => updateSettings({ focusVisible: e.target.checked })}
                        className="form-checkbox h-5 w-5 text-blue-600"
                      />
                      <span className="ml-2 text-gray-700 dark:text-gray-300">Odak Halkasını Göster</span>
                    </label>
                  </div>
                </div>

                {/* Animasyon ve Hareket */}
                <div>
                  <h3 className="flex items-center text-lg font-medium text-gray-900 dark:text-white mb-2">
                    <FiZap className="mr-2" />
                    Animasyon ve Hareket
                  </h3>
                  <div className="flex flex-col space-y-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={settings.reduceMotion}
                        onChange={(e) => updateSettings({ reduceMotion: e.target.checked })}
                        className="form-checkbox h-5 w-5 text-blue-600"
                      />
                      <span className="ml-2 text-gray-700 dark:text-gray-300">Animasyonları Azalt</span>
                    </label>
                  </div>
                </div>

                {/* Ekran Okuyucu */}
                <div>
                  <h3 className="flex items-center text-lg font-medium text-gray-900 dark:text-white mb-2">
                    <FiVolume2 className="mr-2" />
                    Ekran Okuyucu
                  </h3>
                  <div className="flex flex-col space-y-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={settings.screenReaderMode}
                        onChange={(e) => updateSettings({ screenReaderMode: e.target.checked })}
                        className="form-checkbox h-5 w-5 text-blue-600"
                      />
                      <span className="ml-2 text-gray-700 dark:text-gray-300">Ekran Okuyucu Modunu Etkinleştir</span>
                    </label>
                  </div>
                  <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                    Bu mod, ekran okuyucu kullanıcıları için ekstra açıklamalar ve iyileştirilmiş etkileşimler sağlar.
                  </p>
                </div>

                {/* Ayarları Sıfırla */}
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <Button
                    onClick={resetSettings}
                    variant="secondary"
                    fullWidth
                  >
                    Varsayılan Ayarlara Sıfırla
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default AccessibilityPanel;