/**
 * Configuración de entorno de PRODUCCIÓN para despliegue en Render Cloud.
 * Reemplaza 'https://TU-BACKEND-RENDER.onrender.com/api/v1' con la URL pública
 * que te asigne Render al crear el Web Service de FastAPI.
 */
export const environment = {
  production: true,
  apiUrl: 'https://fashionstore-backend-se9f.onrender.com/api/v1',
};
