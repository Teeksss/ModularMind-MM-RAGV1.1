import React from 'react'
import { FiInfo, FiChevronRight, FiCheck, FiAlertTriangle, FiHelpCircle } from 'react-icons/fi'

import Layout from '@/layouts/DashboardLayout'

const EmbeddingHelp: React.FC = () => {
  return (
    <Layout title="Çoklu Embedding Kılavuzu">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="bg-white shadow-sm rounded-lg border p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">ModularMind RAG Platformu Çoklu Embedding Desteği</h1>
          
          <div className="prose max-w-none">
            <p>
              ModularMind platformu, RAG uygulamalarınız için çoklu embedding modellerini destekler.
              Bu sayede farklı diller, alanlardaki metinler ve çeşitli veri türleri için en uygun modelleri kullanabilirsiniz.
            </p>
            
            <h2>Çoklu Embedding'in Avantajları</h2>
            
            <ul>
              <li>Dile özgü modeller ile çok dilli uygulamalar oluşturma</li>
              <li>Alan-spesifik modeller ile domaine özel başarım artışı</li>
              <li>Farklı boyutlu vektörler ile performans/kalite optimizasyonu</li>
              <li>Model karşılaştırması yaparak en iyi modeli seçme</li>
              <li>Otomatik model yönlendirme ile akıllı veri arama</li>
            </ul>
            
            <h2>Desteklenen Model Sağlayıcılar</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
              <div className="border rounded-md p-4">
                <h3 className="text-lg font-medium flex items-center">
                  <FiCheck className="text-green-500 mr-2" /> OpenAI Embeddings
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  text-embedding-3-small, text-embedding-3-large ve tüm OpenAI embedding modelleri
                </p>
              </div>
              
              <div className="border rounded-md p-4">
                <h3 className="text-lg font-medium flex items-center">
                  <FiCheck className="text-green-500 mr-2" /> Azure OpenAI
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  Azure üzerinde dağıtılan tüm OpenAI embedding modelleri
                </p>
              </div>
              
              <div className="border rounded-md p-4">
                <h3 className="text-lg font-medium flex items-center">
                  <FiCheck className="text-green-500 mr-2" /> Cohere
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  Cohere Embed V3 ve diğer tüm Cohere embedding modelleri
                </p>
              </div>
              
              <div className="border rounded-md p-4">
                <h3 className="text-lg font-medium flex items-center">
                  <FiCheck className="text-green-500 mr-2" /> Yerel Modeller
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  Sentence-Transformers kütüphanesi üzerinden tüm HuggingFace modelleri
                </p>
              </div>
            </div>
            
            <h2>Nasıl Kullanılır?</h2>
            
            <h3>1. Doküman Eklerken Çoklu Model Kullanımı</h3>
            
            <p>
              Dokümanlarınızı eklerken birden fazla embedding modeliyle indeksleme yapabilirsiniz:
            </p>
            
            <pre className="bg-gray-50 p-4 rounded-md overflow-auto text-sm">
{`// Doküman yükleme API isteği
fetch('/api/rag/documents', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    document: {
      text: "Doküman metni...",
      metadata: { title: "Doküman başlığı" }
    },
    // Aynı anda birden fazla model için embedding oluşturma
    embedding_models: ["text-embedding-3-small", "all-MiniLM-L6-v2"]
  })
})`}
            </pre>
            
            <h3>2. Akıllı Model Yönlendirmesi</h3>
            
            <p>
              Platform, sorgularınızı analiz ederek en uygun modele yönlendirebilir:
            </p>
            
            <pre className="bg-gray-50 p-4 rounded-md overflow-auto text-sm">
{`// Akıllı model yönlendirmeli sorgu
fetch('/api/rag/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "Bu bir sorgu örneğidir?",
    use_auto_routing: true // Otomatik model seçimi
  })
})`}
            </pre>
            
            <h3>3. Çoklu Model ile Hibrit Arama</h3>
            
            <p>
              Birden fazla model kullanarak hibrit arama yapabilirsiniz:
            </p>
            
            <pre className="bg-gray-50 p-4 rounded-md overflow-auto text-sm">
{`// Çoklu model ile arama
fetch('/api/rag/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "Arama sorgusu",
    use_multi_model: true,
    models_to_use: ["text-embedding-3-small", "all-MiniLM-L6-v2"],
    search_type: "hybrid"
  })
})`}
            </pre>
          </div>
        </div>
        
        <div className="bg-white shadow-sm rounded-lg border p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Önerilen Kullanım Senaryoları</h2>
          
          <div className="space-y-4">
            <div className="border rounded-md p-4">
              <h3 className="text-lg font-medium flex items-center">
                <FiChevronRight className="text-primary-600 mr-2" /> Çok Dilli Belgeler
              </h3>
              <p className="mt-2">
                Farklı dillerdeki belgeleriniz için dile özgü modeller kullanın. Örneğin Türkçe metinler için BERT tabanlı Türkçe modeller, İngilizce metinler için OpenAI modelleri kullanarak her dilde optimum performans elde edin.
              </p>
            </div>
            
            <div className="border rounded-md p-4">
              <h3 className="text-lg font-medium flex items-center">
                <FiChevronRight className="text-primary-600 mr-2" /> Domain-Spesifik Uygulamalar
              </h3>
              <p className="mt-2">
                Hukuk, tıp, finans gibi özel alanlarda domain-spesifik embedding modelleri kullanarak ilgili alandaki terimler ve kavramlar arasındaki ilişkileri daha doğru şekilde yakalayın.
              </p>
            </div>
            
            <div className="border rounded-md p-4">
              <h3 className="text-lg font-medium flex items-center">
                <FiChevronRight className="text-primary-600 mr-2" /> Model Performans Karşılaştırması
              </h3>
              <p className="mt-2">
                Aynı veri seti üzerinde birden fazla model kullanarak hangi modelin sizin veriniz için en iyi sonucu verdiğini analiz edin ve veriye dayalı model seçimi yapın.
              </p>
            </div>
            
            <div className="border rounded-md p-4">
              <h3 className="text-lg font-medium flex items-center">
                <FiChevronRight className="text-primary-600 mr-2" /> Ensemble Modeller
              </h3>
              <p className="mt-2">
                Farklı özelliklere sahip modellerin güçlü yanlarını birleştirerek sonuçları iyileştirin. Örneğin yerel dilde güçlü bir model ile genel bilgide güçlü bir modeli birlikte kullanarak daha kapsamlı sonuçlar elde edin.
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-blue-50 shadow-sm rounded-lg border border-blue-200 p-6">
          <h2 className="text-xl font-bold text-blue-900 mb-4 flex items-center">
            <FiHelpCircle className="mr-2" /> Öneriler ve İpuçları
          </h2>
          
          <div className="space-y-3">
            <div className="flex items-start">
              <FiInfo className="text-blue-500 mt-1 mr-3 flex-shrink-0" />
              <p className="text-blue-800">
                <strong>Doğru model boyutunu seçin:</strong> Daha büyük modeller (daha yüksek boyutlu vektörler) genellikle daha iyi performans gösterir, ancak daha fazla depolama alanı ve işlem gücü gerektirir.
              </p>
            </div>
            
            <div className="flex items-start">
              <FiInfo className="text-blue-500 mt-1 mr-3 flex-shrink-0" />
              <p className="text-blue-800">
                <strong>Her dokümana tüm modelleri uygulamayın:</strong> Tüm belgeleriniz için tüm modelleri kullanmak yerine, belge diline veya türüne göre uygun modelleri seçici şekilde uygulayın.
              </p>
            </div>
            
            <div className="flex items-start">
              <FiAlertTriangle className="text-yellow-500 mt-1 mr-3 flex-shrink-0" />
              <p className="text-blue-800">
                <strong>İndeks boyutunu izleyin:</strong> Çok sayıda model ve belge, indeks boyutunu hızla artırabilir. Depolama ve bellek kullanımını düzenli olarak kontrol edin.
              </p>
            </div>
            
            <div className="flex items-start">
              <FiAlertTriangle className="text-yellow-500 mt-1 mr-3 flex-shrink-0" />
              <p className="text-blue-800">
                <strong>API maliyetlerini göz önünde bulundurun:</strong> OpenAI gibi API tabanlı modeller kullanırken, çoklu modellerin API maliyetlerini artırabileceğini unutmayın.
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}

export default EmbeddingHelp