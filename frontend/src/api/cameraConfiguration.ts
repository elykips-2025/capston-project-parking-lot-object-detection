import { apiFetch } from "./client";

export interface ReferenceImageUploadResult {
  camera_id: string;
  reference_image_storage_key: string;
  width: number;
  height: number;
  format: string;
}

export async function uploadCameraReferenceImage(
  organisationId: string,
  siteId: string,
  cameraId: string,
  file: File,
): Promise<ReferenceImageUploadResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(
    `/organisations/${organisationId}/sites/${siteId}/cameras/${cameraId}/reference-image`,
    {
      method: "PUT",
      body: formData,
    },
  );

  return (await response.json()) as ReferenceImageUploadResult;
}
