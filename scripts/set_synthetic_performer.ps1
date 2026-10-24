<# Write Windows Tags through the native JPEG property handler to a NEW file. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
try {
    $sourcePath = (Resolve-Path -LiteralPath $Source).ProviderPath
    $destination = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
    if ([IO.Path]::GetExtension($sourcePath).ToLowerInvariant() -notin @('.jpg', '.jpeg')) {
        throw 'This Windows Tags writer supports final JPEG files. Export PNG masters to JPEG through a permitted image workflow first.'
    }
    if ([IO.Path]::GetExtension($destination).ToLowerInvariant() -notin @('.jpg', '.jpeg')) {
        throw 'Output must use a .jpg or .jpeg filename; this writer does not convert image formats.'
    }
    $signature = [IO.File]::ReadAllBytes($sourcePath)
    if ($signature.Length -lt 2 -or $signature[0] -ne 255 -or $signature[1] -ne 216) { throw 'Source is not a real JPEG file.' }
    if (Test-Path -LiteralPath $destination) { throw 'Output already exists; choose a new versioned filename.' }
    if (-not ('AmazonImageKeywords' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class AmazonImageKeywords {
    [StructLayout(LayoutKind.Sequential)]
    public struct PropertyKey { public Guid fmtid; public uint pid; }
    [StructLayout(LayoutKind.Explicit, Size = 24)]
    public struct PropVariant { [FieldOffset(0)] public ushort vt; }
    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPropertyStore {
        [PreserveSig] int GetCount(out uint count);
        [PreserveSig] int GetAt(uint index, out PropertyKey key);
        [PreserveSig] int GetValue(ref PropertyKey key, out PropVariant value);
        [PreserveSig] int SetValue(ref PropertyKey key, ref PropVariant value);
        [PreserveSig] int Commit();
    }
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = true)]
    static extern int SHGetPropertyStoreFromParsingName(string path, IntPtr bind, uint flags, ref Guid iid, out IPropertyStore store);
    [DllImport("propsys.dll", CharSet = CharSet.Unicode, PreserveSig = true)]
    static extern int InitPropVariantFromStringVector([MarshalAs(UnmanagedType.LPArray, ArraySubType = UnmanagedType.LPWStr)] string[] values, uint count, out PropVariant value);
    [DllImport("ole32.dll", PreserveSig = true)]
    static extern int PropVariantClear(ref PropVariant value);
    public static void Write(string path, string[] keywords) {
        Guid iid = new Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99");
        IPropertyStore store = null;
        PropVariant value = new PropVariant();
        try {
            Marshal.ThrowExceptionForHR(SHGetPropertyStoreFromParsingName(path, IntPtr.Zero, 2, ref iid, out store));
            Marshal.ThrowExceptionForHR(InitPropVariantFromStringVector(keywords, (uint)keywords.Length, out value));
            PropertyKey key = new PropertyKey { fmtid = new Guid("F29F85E0-4FF9-1068-AB91-08002B27B3D9"), pid = 5 };
            Marshal.ThrowExceptionForHR(store.SetValue(ref key, ref value));
            Marshal.ThrowExceptionForHR(store.Commit());
        } finally {
            PropVariantClear(ref value);
            if (store != null) Marshal.ReleaseComObject(store);
        }
    }
}
'@
    }
    $shell = New-Object -ComObject Shell.Application
    $folder = $shell.NameSpace([IO.Path]::GetDirectoryName($sourcePath))
    $item = $folder.ParseName([IO.Path]::GetFileName($sourcePath))
    $keywords = @($item.ExtendedProperty('System.Keywords') | Where-Object { $_ })
    $tag = 'contains-synthetic-performer'
    if ($keywords -cnotcontains $tag) { $keywords += $tag }
    [IO.File]::Copy($sourcePath, $destination, $false)
    [AmazonImageKeywords]::Write($destination, [string[]]$keywords)
    $writtenFolder = $shell.NameSpace([IO.Path]::GetDirectoryName($destination))
    $writtenItem = $writtenFolder.ParseName([IO.Path]::GetFileName($destination))
    $written = @($writtenItem.ExtendedProperty('System.Keywords'))
    if ($written -cnotcontains $tag) { throw 'Windows System.Keywords read-back did not contain the exact marker; output is not verified.' }
    [pscustomobject]@{ path = $destination; tag = $tag; windows_tags_verified = $true; keywords = $written; xmp_verification = 'Run verify_images with --synthetic-performer on this final file.' } | ConvertTo-Json -Depth 3
    exit 0
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
