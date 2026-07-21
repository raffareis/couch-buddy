namespace BpBinReader;
public interface ITypeSchemaProvider {
    TypeSchema Resolve(Guid typeId);
    bool GetEnumName(TypeSchema enumType, object value, out object representation);
    string GetLocalizedStringText(string key);
    bool UseStringAssetIdType { get; }
    bool SerializedFieldName { get; } 
}
