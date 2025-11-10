import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Upload, File, FileText, Image, X, Download } from "lucide-react";
import { toast } from "sonner@2.0.3";

interface UploadedMaterial {
  id: string;
  name: string;
  type: string;
  size: string;
  uploadDate: string;
}

export function MaterialsUploadPanel() {
  const [materials, setMaterials] = useState<UploadedMaterial[]>([
    {
      id: "1",
      name: "Lecture Slides.pdf",
      type: "pdf",
      size: "2.4 MB",
      uploadDate: "Oct 10, 2025",
    },
    {
      id: "2",
      name: "Reading Material.docx",
      type: "document",
      size: "1.2 MB",
      uploadDate: "Oct 9, 2025",
    },
  ]);

  const handleFileUpload = () => {
    // Simulate file upload
    const newFile: UploadedMaterial = {
      id: `${Date.now()}`,
      name: "New Document.pdf",
      type: "pdf",
      size: "3.1 MB",
      uploadDate: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
    };
    setMaterials([...materials, newFile]);
    toast.success("Material uploaded successfully!");
  };

  const handleDelete = (id: string) => {
    setMaterials(materials.filter((m) => m.id !== id));
    toast.success("Material removed");
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case "pdf":
        return <FileText className="size-4 text-red-500" />;
      case "image":
        return <Image className="size-4 text-blue-500" />;
      default:
        return <File className="size-4 text-gray-500" />;
    }
  };

  return (
    <Card className="flex flex-col h-full overflow-hidden">
      <CardHeader className="shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Learning Materials</CardTitle>
            <CardDescription>Upload materials to enhance AI note generation</CardDescription>
          </div>
          <Button size="sm" onClick={handleFileUpload} className="gap-2">
            <Upload className="size-4" />
            Upload
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 overflow-hidden">
        <ScrollArea className="h-full pr-4">
          {materials.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-center text-muted-foreground">
              <Upload className="size-8 mb-2 opacity-50" />
              <p className="text-sm">No materials uploaded yet</p>
              <p className="text-xs">Upload PDFs, documents, or images to help AI generate better notes</p>
            </div>
          ) : (
            <div className="space-y-2">
              {materials.map((material) => (
                <div
                  key={material.id}
                  className="border rounded-lg p-3 hover:bg-accent transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <div className="mt-0.5">
                        {getFileIcon(material.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm truncate">{material.name}</h4>
                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                          <span>{material.size}</span>
                          <span>•</span>
                          <span>{material.uploadDate}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => toast.info("Download feature")}
                        className="size-7 p-0"
                      >
                        <Download className="size-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(material.id)}
                        className="size-7 p-0 hover:bg-destructive/10 hover:text-destructive"
                      >
                        <X className="size-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}